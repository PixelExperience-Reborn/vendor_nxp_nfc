#!/usr/bin/env python3
"""Pinned source-only Android17 NXP NFC boundary check; not a Soong/device test."""
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

OLD_SHA = "b5b0dcca7c7faf6b1dce696c864dd7f43a78e472"
OLD_TREE = "ca1b801079383abc39d69742ec4d671ff95a2a65"
AOSP17_SHA = "68931d93d3b2ccfc71553cb03088fe5d6fb5dd30"
AOSP17_TREE = "8386a3c67e07f5fe492c92d1888c256bbc37d48b"
COMMON_SHA = "6e0022f5100e09ac97980095b6ed8528f4ff823f"


def git(repo, *args):
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], text=True).strip()


def source(repo, ref, file):
    return git(repo, "show", f"{ref}:{file}")


def require(condition, reason):
    if not condition:
        raise RuntimeError(reason)


def pinned(repo, ref, expected_sha, expected_tree, label):
    sha = git(repo, "rev-parse", f"{ref}^{{commit}}")
    require(sha == expected_sha, f"{label}: commit changed ({sha})")
    if expected_tree:
        tree = git(repo, "rev-parse", f"{sha}^{{tree}}")
        require(tree == expected_tree, f"{label}: tree changed ({tree})")
    return sha


def historical(repo):
    rev = pinned(repo, "refs/remotes/origin/seventeen",
                 OLD_SHA, OLD_TREE, "old PE NFC")
    bp = source(repo, rev, "Android.bp")
    product = source(repo, rev, "nfc-vendor-product.mk")
    rc = source(repo, rev, "1.2/android.hardware.nfc@1.2-service.pn8x.rc")
    vif = ET.fromstring(source(
        repo, rev, "1.2/android.hardware.nfc@1.2-service.pn8x.xml"))
    require('name: "android.hardware.nfc@1.2-service.pn8x"' in bp
            and '"android.hardware.nfc@1.2"' in bp,
            "old HIDL 1.2 service source contract changed")
    require('imports: ["vendor/nxp/secure_element"]' in bp,
            "old Secure Element namespace contract changed")
    require("NXP_NFC_HARDWARE := PN81T" in product
            and "android.hardware.nfc@1.2-service.pn8x" in product
            and "vendor/nxp/secure_element" in product,
            "old PN81T example product wiring changed")
    require("service vendor.nfc_hal_service" in rc,
            "old HIDL init service contract changed")
    hal_names = [h.findtext("name") for h in vif.findall("hal")]
    require(set(hal_names) == {
        "android.hardware.nfc", "vendor.nxp.nxpnfc",
        "vendor.nxp.nxpnfclegacy"}, "old service VINTF HAL set changed")
    require(vif.find(".//hal[name='android.hardware.nfc']/version").text
            == "1.2", "old NFC HIDL version changed")
    print("PASS: old PE NFC tree is pinned and declares PN81T/HIDL1.2 service")


def official(repo):
    rev = pinned(repo, "FETCH_HEAD", AOSP17_SHA, AOSP17_TREE,
                 "official AOSP17 NXP NFC")
    bp = source(repo, rev, "snxxx/Android.bp")
    require('name: "android.hardware.nfc-service.nxp"' in bp,
            "official Android17 NXP AIDL service disappeared")
    require('"android.hardware.nfc-V1-ndk"' in bp
            and 'nfc-service-nxp.xml' in bp,
            "official NXP AIDL/VINTF wiring changed; re-audit")
    print("PASS: exact official AOSP17 NXP NFC tree provides modern AIDL HAL")


def device_reference(repo):
    rev = pinned(repo, "HEAD", COMMON_SHA, None,
                 "mondrian sm8450-common read-only reference")
    mk = source(repo, rev, "common.mk")
    blobs = source(repo, rev, "proprietary-files.txt")
    board = source(repo, rev, "BoardConfigCommon.mk")
    vif = ET.fromstring(source(repo, rev, "vintf/manifest_nfc.xml"))
    require("android.hardware.nfc-service.nxp" in mk
            and "android.hardware.nfc@1.2-service.pn8x" not in mk,
            "mondrian NFC service selection changed")
    require("vendor/lib64/libsn100u_fw.so" in blobs,
            "known-good vendor firmware inventory changed")
    require("TARGET_NFC_SUPPORTED_SKUS" in mk
            and "TARGET_NFC_SUPPORTED_SKUS" in board,
            "device NFC SKU split changed")
    se = next((h for h in vif.findall("hal")
               if h.findtext("name") == "android.hardware.secure_element"), None)
    require(se is not None and se.attrib.get("format") == "hidl"
            and se.findtext("version") == "1.2",
            "mondrian secure_element VINTF contract changed")
    instances = {e.text for e in se.findall(".//instance")}
    require(instances == {"eSE1", "SIM1", "SIM2"},
            "mondrian eSE/SIM instance inventory changed")
    require(any(h.findtext("name") == "vendor.qti.esepowermanager"
                for h in vif.findall("hal")),
            "eSEPowerManager routing changed")
    print("PASS: pinned sm8450-common has NXP AIDL, SN100 firmware and eSE/SIM split")


def manifest_boundary(repo):
    root = Path(repo)
    entry = ET.parse(root / "default.xml").getroot()
    require(len(entry) == 1 and entry[0].get("name")
            == "aosp17_pe_p2_kernel_configs.xml",
            "reviewed AOSP17 manifest entrypoint changed")
    base = ET.parse(root / "aosp17_pe_bootstrap.xml").getroot()
    mapping = {p.get("path"): p.get("name") for p in base.findall("project")}
    require(mapping.get("hardware/nxp/nfc") == "platform/hardware/nxp/nfc",
            "official AOSP17 hardware/nxp/nfc owner changed")
    require(mapping.get("packages/modules/Nfc") == "platform/packages/modules/Nfc",
            "official AOSP17 NFC Mainline source owner changed")
    require("vendor/nxp/nfc" not in mapping
            and "vendor_nxp_nfc" not in mapping.values(),
            "old NXP HAL has been activated")
    subprocess.run([sys.executable,
                    str(root / "tools/validate_aosp17_base_profiles.py")],
                   cwd=root, check=True)
    print("PASS: 25 staged AOSP17 source profiles retain official NFC owners")


def main():
    require(len(sys.argv) == 5,
            "Usage: check_nfc_boundary.py LEGACY_PE AOSP17_NXP MONDRIAN_COMMON AOSP17_MANIFEST")
    old, aosp, common, manifest = map(Path, sys.argv[1:])
    require(all(p.is_dir() for p in (old, aosp, common, manifest)),
            "one or more checked-out source directories missing")
    historical(old)
    official(aosp)
    device_reference(common)
    manifest_boundary(manifest)
    print("PASS: row 165 NXP NFC source-only compatibility boundary")
    print("OPEN: independent PE device/product, NFC Soong, eSE VINTF/SELinux,")
    print("      Mainline NFC/APEX, Xiaomi vendor ABI, real mondrian NFC tests")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, ValueError, ET.ParseError,
            subprocess.CalledProcessError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)

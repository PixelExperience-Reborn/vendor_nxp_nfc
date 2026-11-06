# Android 17 — NXP NFC hardware boundary audit (manifest row 165)

**Date:** 2026-11-07. **Target:** POCO F5 Pro / Redmi K60 (mondrian, SM8475/SM8450 family).
**Scope:** historical PixelExperience-Reborn `vendor/nxp/nfc` against the Android 17 source graph.
**Status:** architecture/source-only audit; NFC HAL compilation, VINTF compatibility, secure-element operation and device runtime are NOT tested.

## Decision

**Do not enable the old `vendor_nxp_nfc` HIDL 1.2 PN8x repository in the active Android17 manifest.** Android17 already selects upstream `platform/hardware/nxp/nfc` and `platform/packages/modules/Nfc`. The working LF52406 sm8450-common configuration uses the NXP AIDL service `android.hardware.nfc-service.nxp`, rather than the old `android.hardware.nfc@1.2-service.pn8x`. Enabling the old service creates an unreviewed additional HAL/service and can duplicate INfc/default, init services, VINTF declarations, firmware configuration and SELinux policy. This is an integration risk; no actual collision or exploit was demonstrated.

This is **not** a decision to drop NXP NFC, drop secure element support, or replace an operational Xiaomi hardware stack with a generic chip driver. The independent PE-Reborn mondrian device/common/product trees have not yet been implemented. Existing LF52406 device trees are valuable read-only hardware references, not active PE-Reborn build inputs.

## Source evidence (immutable checks)

| Source | Revision | Relevant contract |
| --- | --- | --- |
| PE `vendor_nxp_nfc` `seventeen` | `b5b0dcca7c7faf6b1dce696c864dd7f43a78e472`, tree `ca1b801079383abc39d69742ec4d671ff95a2a65` | `Android.bp` exports `android.hardware.nfc@1.2-service.pn8x`; the service XML declares HIDL `android.hardware.nfc` 1.2 INfc/default plus vendor.nxp extensions; Soong imports `vendor/nxp/secure_element`. |
| PE `nfc-vendor-product.mk` (same SHA) | as above | Sets `NXP_NFC_HARDWARE := PN81T`, copies example PN81T NXP/RF configuration and old vendor permissions, and installs the HIDL 1.2 service. This is **not proof** that mondrian has PN81T. |
| Official AOSP17 `hardware/nxp/nfc` | tag `android-17.0.0_r1`, peeled commit `68931d93d3b2ccfc71553cb03088fe5d6fb5dd30`, tree `8386a3c67e07f5fe492c92d1888c256bbc37d48b` | AOSP owns `hardware/nxp/nfc`. Its `snxxx/Android.bp` defines the NXP AIDL service `android.hardware.nfc-service.nxp`; the official source also retains other hardware variants. Choosing a variant belongs to the device product configuration. |
| LF52406 `sm8450-common` | `lineage-24.0`, `6e0022f5100e09ac97980095b6ed8528f4ff823f` | `common.mk` packages NXP AIDL service; `proprietary-files.txt` lists `vendor/lib64/libsn100u_fw.so`. `vintf/manifest_nfc.xml` carries secure-element HIDL 1.2 eSE1/SIM1/SIM2 and vendor eSEPowerManager, not an additional NFC HIDL 1.2 default HAL. SKU-specific permissions/manifest are conditional. |
| PE-Reborn AOSP17 manifest | `port/a17-aosp17-manifest-20261102`, reviewed starting commit `c0b63bc2ad54b5e687003dee3c3d01308fbae39f` | The staged graph selects `platform/hardware/nxp/nfc` and `platform/packages/modules/Nfc`; the historical `snippets/pixel-caf.xml` remains inactive. |

Additional release source: NXP publishes the **17.07.00** Android17 NXP NFC source series on `br_ar_17_aosp_mainline`, supporting PN557/PN560/SN100/SN110/SN220/SN300. A modern available release does **not**, by itself, establish a safe upgrade path for Xiaomi firmware/SE calibration or a specific NFC controller variant.

- AOSP tag: https://android.googlesource.com/platform/hardware/nxp/nfc/+/refs/tags/android-17.0.0_r1
- NXP Android17 release record: https://github.com/NXPNFCProject/nfcandroid_nfc_hidlimpl
- Android17 Mainline NFC app: https://android.googlesource.com/platform/packages/modules/Nfc/+/refs/tags/android-17.0.0_r1
- Hardware reference: https://github.com/LF52406/mondrian_android_device_xiaomi_sm8450-common/tree/lineage-24.0
- Active AOSP17 manifest: https://github.com/PixelExperience-Reborn/manifest/tree/port/a17-aosp17-manifest-20261102

## Non-negotiable AOSP17/NFC ownership

1. Keep exactly one selected `hardware/nxp/nfc` source owner and one `packages/modules/Nfc` owner. Do **not** activate `vendor/nxp/nfc` or the legacy `vendor_nxp_nfc` fork.
2. Keep one `android.hardware.nfc.INfc/default` provider with a matching AIDL/HIDL framework/VINTF contract. Do not ship AIDL and the archived PN8x HIDL default providers together.
3. Preserve the separation between NFC controller HAL, secure-element HAL, eSE/SIM routes and NFC app/APEX. Do not assume Secure Element is optional just because the NFC core HAL is AIDL.
4. No global SELinux `permissive`, broad NFC file access or archived HIDL-specific domain/contexts copied from old `vendor/nxp/nfc/sepolicy` into Android17.
5. Do not overwrite device-specific `libnfc-nxp.conf`, `libnfc-nxp_RF.conf`, `libsn100u_fw.so`, secure-element routing or SKU permissions with generic PN81T example files.
6. Do not import old Qualcomm `vendor/nxp/opensource/commonsys/*`, `pn5xx/*`, `sn100x/*` or `secure_element_extns` before their own matrix rows/dependency reviews. NFC app is Mainline `packages/modules/Nfc`; avoid duplicate apps/overlays and module owners.

## Mandatory gates for a future native mondrian port

- **Hardware identity:** verify actual NXP controller and board NFC/eSE routing from existing known-good init/config/kernel nodes, proprietary libraries and a real device dump; the file `libsn100u_fw.so` alone does not conclusively identify every hardware revision.
- **Dependency graph:** identify the exact AOSP17 NXP AIDL service, vendor extensions and secure-element libraries needed by real Xiaomi blobs, including Soong namespaces, `dlopen`/SONAME interfaces and ownership of vendor NFC configuration.
- **VINTF:** run `checkvintf` and target-level compatibility checks for the shipped vendor/odm manifests, AIDL NFC instance and HIDL secure-element/eSEPowerManager instances; test both NFC-capable and NFC-disabled SKU policy rather than guessing.
- **Security:** check vendor init rc, `file_contexts`, `hwservice_contexts`/`service_contexts`, exported interfaces, sepolicy `neverallow`, service identity and permissions in enforcing mode.
- **Build/APEX:** compile Android17 NFC and NXP service with the independent PE-Reborn product, verify correct `packages/modules/Nfc` APEX/APK selection and `NfcResMondrian` resource overlay compatibility. Host source checks do not prove this.
- **Device runtime:** validate power-on/reboot NFC, reader/writer, polling, tag read/write, HCE/payment wallet where supported, eSE/UICC selection, airplane mode, screen-off transitions, multi-user behaviour, cold reboot and vendor NFC logs. Do not change payment security/SE firmware speculatively.
- **Regressions:** verify ADB shell `service list`, `dumpsys nfc`, VINTF, NFC HAL logs, `logcat`/AVC and test cross-SKU behavior before claiming functional NFC.

## Current implementation

- An isolated `audit/a17-mondrian-nxp-nfc-20261107` branch adds this document, a pinned source-contract checker and a CI workflow.
- The manifest's **existing working AOSP17 port branch**, not `seventeen`, is to be updated with explicit official NXP owner and negative tests against accidental legacy activation.
- Historical PE `seventeen` sources remain untouched. LF52406 devices/vendor/kernel and NFC firmware are untouched.
- **No NFC implementation or device/product integration is claimed.** The next row is the separate historical `vendor/nxp/opensource/commonsys/external/libnfc-nci` review, not automatic inclusion here.

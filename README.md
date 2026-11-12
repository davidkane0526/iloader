# HermesEnabler Windows Installer

Windows-only Apple Watch companion-app installer based on [AndreySemjonov/iloader](https://github.com/AndreySemjonov/iloader), tracked against [HermesEnabler issue #54](https://github.com/pookjw/HermesEnabler/issues/54).

This repository stores a pinned upstream source revision, reproducible patches, a dedicated Rust CLI, and GitHub Actions build files. The build downloads upstream sources at the pinned revision, applies local patches, and compiles a Windows executable. No Apple ID credentials are collected by CI. Enter credentials only into the executable running locally on your Windows PC.

**Status:** source-level work, automated build pending. Do not assume HermesEnabler support for any specific watchOS build until verified on the device.

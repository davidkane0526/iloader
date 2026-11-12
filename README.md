# HermesEnabler Windows Installer

Windows-only Apple Watch companion-app installer based on [AndreySemjonov/iloader](https://github.com/AndreySemjonov/iloader), tracked against [HermesEnabler issue #54](https://github.com/pookjw/HermesEnabler/issues/54).

This repository stores a pinned upstream source revision, reproducible patches, a dedicated Rust CLI, and GitHub Actions build files. The build downloads upstream sources at the pinned revision, applies local patches, and compiles a Windows executable. No Apple ID credentials are collected by CI. Enter credentials only into the executable running locally on your Windows PC.

**CI status:** [Windows compilation passed](https://github.com/davidkane0526/iloader/actions/runs/43153944527) on 2026-11-12. The EXE is a 12,387,840-byte Windows x64 console application. SHA-256: `923c7fe46b792d9f6a427165c41d1767e842b83ce274d9efa220743c6db626b1`. **Physical-device compatibility remains unverified.**

See [中文说明](README-中文.md).
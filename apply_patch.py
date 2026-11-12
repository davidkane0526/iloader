#!/usr/bin/env python3
"""Apply Issue #54 patches to AndreySemjonov/iloader (pinned revision)."""
import argparse
from pathlib import Path

BASELINE = "2d13485ef2d7107b2bc2ec6cdb5f54ce5729ef70"

def edit(root, relative, replacements):
    file = root / relative
    source = file.read_text(encoding="utf-8")
    for original, replacement, title in replacements:
        if replacement in source:
            print(f"Already patched: {title}")
            continue
        count = source.count(original)
        if count != 1:
            raise RuntimeError(f"{title}: expected 1 original occurrence, found {count}; check source revision")
        source = source.replace(original, replacement, 1)
        print(f"Patched: {title}")
    file.write_text(source, encoding="utf-8")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    if not (root / "vendor/isideload/isideload/src/sideload/sideloader.rs").is_file():
        raise RuntimeError("Not a supported upstream iLoader checkout")

    edit(root, "vendor/isideload/isideload/src/anisette/remote_v3/mod.rs", [
        ('pub const DEFAULT_ANISETTE_V3_URL: &str = "https://ani.stikstore.app";',
         'pub const DEFAULT_ANISETTE_V3_URL: &str = "https://ani.jkcoxson.com";',
         "Anisette default"),
        ("pub enum Endpoint {\n    Headers,\n    Provisioning,\n}",
         "pub enum Endpoint {\n    Headers,\n    Provisioning,\n    ClientInfo,\n}",
         "client-info endpoint enum"),
        ('Endpoint::Headers => "get_headers",\n        Endpoint::Provisioning => "provisioning_session",',
         'Endpoint::Headers => "get_headers",\n        Endpoint::Provisioning => "provisioning_session",\n        Endpoint::ClientInfo => "client_info",',
         "client-info endpoint routing"),
        ('''    async fn get_client_info(&self) -> Result<AnisetteClientInfo, Report> {
        Ok(AnisetteClientInfo {
            client_info:
                "<Mac15,7> <macOS;27.0;26A5378j> <com.apple.AuthKit/1 (com.apple.akd/1.0)>"
                    .to_string(),
            user_agent: "akd/1.0 CFNetwork/808.1.4".to_string(),
        })
    }''',
         '''    async fn get_client_info(&self) -> Result<AnisetteClientInfo, Report> {
        let info = self.client
            .get(endpoint_url(&self.url, Endpoint::ClientInfo)?)
            .send()
            .await?
            .error_for_status()?
            .json::<AnisetteClientInfo>()
            .await
            .context("Failed to parse Anisette server client_info")?;
        if info.client_info.trim().is_empty() || info.user_agent.trim().is_empty() {
            bail!("Anisette server returned empty client_info / user_agent");
        }
        Ok(info)
    }''', "fetch server client-info")
    ])

    edit(root, "vendor/isideload/isideload/src/dev/app_ids.rs", [
        ('''    pub async fn ensure_group_feature(
        &mut self,
        dev_session: &mut DeveloperSession,
        team: &DeveloperTeam,
    ) -> Result<(), Report> {''',
         '''    pub async fn ensure_group_feature(
        &mut self,
        dev_session: &mut DeveloperSession,
        team: &DeveloperTeam,
        device_type: impl Into<Option<DeveloperDeviceType>> + Send,
    ) -> Result<(), Report> {''', "platform-aware App Group feature"),
        ('.update_app_id(team, self, body, None)', '.update_app_id(team, self, body, device_type)',
         "watchOS platform marker for App ID feature")
    ])

    edit(root, "vendor/isideload/isideload/src/sideload/sideloader.rs", [
        ('''        let app_group = self
            .dev_session
            .ensure_app_group(&team, &main_app_name, &group_identifier, None)
            .await?;

        for app_id in app_ids.iter_mut() {
            if watch_bundle_ids.contains(&app_id.identifier) {
                continue;
            }

            app_id
                .ensure_group_feature(&mut self.dev_session, &team)
                .await?;

            self.dev_session
                .assign_app_group(&team, &app_group, app_id, None)
                .await?;
''',
         '''        let app_group = self
            .dev_session
            .ensure_app_group(&team, &main_app_name, &group_identifier, None)
            .await?;
        let watch_group = if watch_bundle_ids.is_empty() {
            None
        } else {
            Some(self.dev_session.ensure_app_group(
                &team,
                &main_app_name,
                &group_identifier,
                Some(DeveloperDeviceType::Watchos),
            ).await?)
        };

        for app_id in app_ids.iter_mut() {
            let is_watch = watch_bundle_ids.contains(&app_id.identifier);
            let device_type = if is_watch {
                Some(DeveloperDeviceType::Watchos)
            } else {
                None
            };
            app_id
                .ensure_group_feature(&mut self.dev_session, &team, device_type.clone())
                .await?;

            let group = if is_watch {
                watch_group.as_ref().ok_or_else(|| report!("Watch App Group unavailable"))?
            } else {
                &app_group
            };
            self.dev_session
                .assign_app_group(&team, group, app_id, device_type)
                .await?;
''', "assign App Group to embedded Watch apps"),
        ('''            let parsed_profile = ProvisioningProfile::parse(profile.encoded_profile.as_ref())?;
            let entitlements = parsed_profile.entitlements().clone();

            provisioning_profiles.push((bundle_id, profile, entitlements));''',
         '''            let parsed_profile = ProvisioningProfile::parse(profile.encoded_profile.as_ref())?;
            let entitlements = parsed_profile.entitlements().clone();
            if watch_bundle_ids.contains(&bundle_id) {
                let groups = entitlements
                    .get("com.apple.security.application-groups")
                    .and_then(|value| value.as_array())
                    .ok_or_else(|| report!("Watch provisioning profile lacks App Group: {}", bundle_id))?;
                if !groups.iter().any(|v| v.as_string() == Some(group_identifier.as_str())) {
                    bail!("Watch provisioning profile missing group {} for {}", group_identifier, bundle_id);
                }
            }

            provisioning_profiles.push((bundle_id, profile, entitlements));''',
         "verify watchOS profile App Group entitlement"),
    ])

    edit(root, "vendor/isideload/isideload/Cargo.toml", [
        ('apple-codesign = { git = "https://github.com/nab138/apple-crates", version = "0.1.0", package = "apple-codesign" }',
         'apple-codesign = { git = "https://github.com/nab138/apple-crates", rev = "5da0b8df9b202434b1eff2700059b1ee142592ac", version = "0.1.0", package = "apple-codesign" }',
         "pin apple-codesign to revision in upstream lockfile")
    ])
    print("Patch complete. No user credentials are accessed by this script.")

if __name__ == "__main__":
    main()

//! Command-line Windows installer for untouched HermesEnabler IPA.
//! Apple ID credentials are entered into the local console, never GitHub Actions.
use std::{env, io::{self, Write}, path::PathBuf};

use idevice::{
    usbmuxd::{Connection, UsbmuxdAddr, UsbmuxdConnection},
};
use isideload::{
    anisette::remote_v3::RemoteV3AnisetteProvider,
    auth::apple_account::{AppleAccount, TwoFactorCallbackParams, TwoFactorCallbackResponse},
    dev::{certificates::DevelopmentCertificate, developer_session::DeveloperSession},
    sideload::{SideloaderBuilder, builder::MaxCertsBehavior},
    util::keyring_storage::KeyringStorage,
};
use rootcause::prelude::*;

const ANIS: &str = "https://ani.jkcoxson.com";
const SERVICE: &str = "hermes-iloader-cli";

fn prompt(message: &str) -> io::Result<String> {
    print!("{message}");
    io::stdout().flush()?;
    let mut input = String::new();
    io::stdin().read_line(&mut input)?;
    Ok(input.trim().to_string())
}

fn on_certificate_limit(certs: &Vec<DevelopmentCertificate>) -> Option<Vec<String>> {
    eprintln!("\nApple developer certificate limit reached.");
    eprintln!("Revocation invalidates other apps signed using this certificate.");
    for c in certs {
        eprintln!("Certificate: {:?} | machine: {:?} | serial: {:?}",
            c.name, c.machine_name, c.serial_number);
    }
    let input = prompt("Exact serial to revoke (blank = cancel): ").ok()?;
    if input.is_empty() { return None; }
    if !certs.iter().any(|c| c.serial_number.as_deref() == Some(input.as_str())) {
        eprintln!("Unknown serial; nothing revoked.");
        return None;
    }
    let confirmation = prompt("Type REVOKE to confirm: ").ok()?;
    if confirmation == "REVOKE" { Some(vec![input]) } else { None }
}

async fn ask_2fa(params: TwoFactorCallbackParams) -> Result<TwoFactorCallbackResponse, Report> {
    if let Some(message) = params.last_error.as_deref() {
        eprintln!("Previous 2FA attempt failed: {message}");
    }
    if params.unknown {
        eprintln!("Requesting a verification code from a trusted Apple device...");
        return Ok(TwoFactorCallbackResponse::SendToDevices);
    }
    if params.sms {
        eprintln!("An SMS verification code is required.");
    } else {
        eprintln!("Check your trusted Apple device for the verification code.");
    }
    let code = prompt("Verification code (blank = abort): ")
        .map_err(|e| report!("Unable to read 2FA code: {e}"))?;
    if code.is_empty() { Ok(TwoFactorCallbackResponse::Abort) }
    else { Ok(TwoFactorCallbackResponse::SubmitCode(code)) }
}

async fn run() -> Result<(), String> {
    isideload::init().map_err(|e| format!("Initialization: {e:?}"))?;
    let mut args = env::args_os();
    args.next();
    let input = args.next().ok_or_else(|| "Usage: iloader-cli.exe <original HermesEnabler.ipa>".to_string())?;
    if args.next().is_some() { return Err("Expected exactly one IPA path".into()); }
    let ipa = PathBuf::from(input);
    if ipa.extension().and_then(|x| x.to_str()) != Some("ipa") || !ipa.is_file() {
        return Err(format!("IPA file is missing: {}", ipa.display()));
    }
    println!("iLoader CLI 0.1.0: Windows + Apple Watch companion support");
    println!("IPA: {}", ipa.display());
    println!("Anisette: {ANIS}");

    // Verify USB connection before asking for any credentials.
    let mut usbmux = UsbmuxdConnection::default().await
        .map_err(|e| format!("Apple Mobile Device Service unavailable: {e:?}"))?;
    let devices = usbmux.get_devices().await
        .map_err(|e| format!("Unable to enumerate devices: {e:?}"))?;
    let usb_devices: Vec<_> = devices.into_iter()
        .filter(|device| matches!(&device.connection_type, Connection::Usb))
        .collect();
    if usb_devices.is_empty() {
        return Err("No USB-connected iPhone found. Check iTunes driver and Trust dialog.".into());
    }
    for (i, device) in usb_devices.iter().enumerate() {
        println!("[{}] USB device: {}", i + 1, device.udid);
    }
    let selected = if usb_devices.len() == 1 { 0 } else {
        let input = prompt("Device number: ").map_err(|e| e.to_string())?;
        let n: usize = input.parse().map_err(|_| "Invalid device number".to_string())?;
        if !(1..=usb_devices.len()).contains(&n) { return Err("Invalid device number".into()); }
        n - 1
    };
    let provider = usb_devices[selected]
        .to_provider(UsbmuxdAddr::from_env_var().unwrap(), "hermes-iloader-cli");

    let email = prompt("Apple ID email: ").map_err(|e| e.to_string())?.to_lowercase();
    if !email.contains('@') { return Err("Apple ID email is required".into()); }
    print!("Apple ID password (hidden): ");
    io::stdout().flush().map_err(|e| e.to_string())?;
    let password = rpassword::read_password().map_err(|e| e.to_string())?;
    if password.is_empty() { return Err("Empty password".into()); }

    let anisette = RemoteV3AnisetteProvider::new(
        ANIS, Box::new(KeyringStorage::new(SERVICE.into())), "0".into(),
    ).map_err(|e| format!("Anisette provider: {e:?}"))?;
    let mut account = AppleAccount::builder(&email)
        .anisette_provider(anisette)
        .login(&password, ask_2fa)
        .await.map_err(|e| format!("Apple ID login: {e:?}"))?;
    drop(password);
    let developer = DeveloperSession::from_account(&mut account)
        .await.map_err(|e| format!("Developer session: {e:?}"))?;
    let mut sideloader = SideloaderBuilder::new(developer, email)
        .machine_name("hermes-iloader-cli".into())
        .storage(Box::new(KeyringStorage::new(SERVICE.into())))
        .max_certs_behavior(MaxCertsBehavior::Prompt(Box::new(on_certificate_limit)))
        .build();

    println!("Signing and installing the iPhone app and paired Apple Watch app...");
    sideloader.install_app(
        &provider, ipa, false, None::<fn(f32) -> std::future::Ready<()>>
    ).await.map_err(|e| format!("Install failed: {e:?}"))?;
    println!("DONE: installer reports the app was installed.");
    Ok(())
}

#[tokio::main(flavor = "multi_thread")]
async fn main() {
    let _ = rustls::crypto::ring::default_provider().install_default();
    if let Err(error) = run().await {
        eprintln!("\nERROR: {error}");
        std::process::exit(1);
    }
}

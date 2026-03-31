use tauri_plugin_shell::ShellExt;

/// Run the pdfdiff sidecar with given arguments and return stdout.
async fn run_sidecar(
    app: &tauri::AppHandle,
    args: Vec<&str>,
) -> Result<String, String> {
    let shell = app.shell();
    let command = shell
        .sidecar("pdfdiff")
        .map_err(|e| format!("Failed to create sidecar command: {e}"))?;

    eprintln!("[sidecar] Executing pdfdiff with args: {args:?}");

    let output = command
        .args(args)
        .output()
        .await
        .map_err(|e| format!("Failed to execute sidecar: {e}"))?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        let stdout = String::from_utf8_lossy(&output.stdout);
        eprintln!("[sidecar] Exit code: {:?}", output.status.code());
        eprintln!("[sidecar] stderr: {stderr}");
        eprintln!("[sidecar] stdout: {stdout}");
        return Err(format!("Sidecar error (exit {:?}): {stderr}", output.status.code()));
    }

    String::from_utf8(output.stdout)
        .map_err(|e| format!("Invalid UTF-8 in sidecar output: {e}"))
}

#[tauri::command]
pub async fn diff_pdfs(
    app: tauri::AppHandle,
    left_path: String,
    right_path: String,
) -> Result<String, String> {
    run_sidecar(&app, vec!["diff", &left_path, &right_path, "--json"]).await
}

#[tauri::command]
pub async fn validate_pdf(
    app: tauri::AppHandle,
    pdf_path: String,
    word_spacing_factor: Option<f64>,
) -> Result<String, String> {
    let factor_str;
    let mut args = vec!["validate", &pdf_path, "--json"];

    if let Some(factor) = word_spacing_factor {
        factor_str = factor.to_string();
        args.push("--word-spacing-factor");
        args.push(&factor_str);
    }

    run_sidecar(&app, args).await
}

#[tauri::command]
pub async fn save_annotations(
    app: tauri::AppHandle,
    pdf_path: String,
    output_path: String,
    annotations: String,
) -> Result<(), String> {
    run_sidecar(
        &app,
        vec![
            "annotate",
            &pdf_path,
            &output_path,
            "--annotations",
            &annotations,
        ],
    )
    .await?;
    Ok(())
}

#[tauri::command]
pub async fn visual_diff_pdfs(
    app: tauri::AppHandle,
    left_path: String,
    right_path: String,
    dpi: Option<i32>,
) -> Result<String, String> {
    let dpi_str;
    let mut args = vec!["visual-diff", &left_path, &right_path, "--json"];

    if let Some(d) = dpi {
        dpi_str = d.to_string();
        args.push("--dpi");
        args.push(&dpi_str);
    }

    run_sidecar(&app, args).await
}

#[tauri::command]
pub async fn detect_document_type(
    app: tauri::AppHandle,
    pdf_path: String,
) -> Result<String, String> {
    run_sidecar(&app, vec!["detect", &pdf_path, "--json"]).await
}

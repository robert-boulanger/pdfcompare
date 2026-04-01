use base64::Engine;
use std::path::Path;

#[tauri::command]
pub async fn load_pdf_file(path: String) -> Result<String, String> {
    let file_path = Path::new(&path);

    // Validate .pdf extension
    match file_path.extension().and_then(|e| e.to_str()) {
        Some(ext) if ext.eq_ignore_ascii_case("pdf") => {}
        _ => return Err("Only .pdf files are allowed".into()),
    }

    // Resolve to canonical path to prevent path traversal via symlinks
    let canonical = file_path
        .canonicalize()
        .map_err(|e| format!("Invalid path: {e}"))?;

    // Read file off the main thread
    let bytes = tauri::async_runtime::spawn_blocking(move || std::fs::read(&canonical))
        .await
        .map_err(|e| format!("Task failed: {e}"))?
        .map_err(|e| format!("Failed to read PDF: {e}"))?;

    Ok(base64::engine::general_purpose::STANDARD.encode(&bytes))
}

use base64::Engine;

#[tauri::command]
pub fn load_pdf_file(path: String) -> Result<String, String> {
    let bytes = std::fs::read(&path).map_err(|e| format!("Failed to read PDF: {e}"))?;
    Ok(base64::engine::general_purpose::STANDARD.encode(&bytes))
}

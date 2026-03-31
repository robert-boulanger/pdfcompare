mod commands;

use commands::pdf::load_pdf_file;
use commands::sidecar::{
    detect_document_type, diff_pdfs, save_annotations, validate_pdf, visual_diff_pdfs,
};

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![
            load_pdf_file,
            diff_pdfs,
            validate_pdf,
            save_annotations,
            visual_diff_pdfs,
            detect_document_type,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

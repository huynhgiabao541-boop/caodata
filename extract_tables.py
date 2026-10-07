import os
import pandas as pd
import pdfplumber
import docx
import sys
import urllib3

urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8')

def extract_tables_from_pdf(pdf_path):
    all_tables = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        cleaned_row = [str(cell).strip() if cell is not None else "" for cell in row]
                        all_tables.append(cleaned_row)
    except Exception as e:
        print(f"Lỗi đọc PDF {os.path.basename(pdf_path)}: {e}")
    return all_tables

def extract_tables_from_docx(docx_path):
    all_tables = []
    try:
        doc = docx.Document(docx_path)
        for table in doc.tables:
            for row in table.rows:
                row_data = [cell.text.strip() for cell in row.cells]
                all_tables.append(row_data)
    except Exception as e:
        print(f"Lỗi đọc DOCX {os.path.basename(docx_path)}: {e}")
    return all_tables

def main():
    pdf_dir = r'e:\caodata\caodata\thuocBVTV_pdfs'
    output_excel = r'e:\caodata\caodata\thuocBVTV_tables.xlsx'

    if not os.path.exists(pdf_dir):
        print("Thư mục không tồn tại!")
        return

    files = [f for f in os.listdir(pdf_dir) if f.endswith('.pdf') or f.endswith('.docx')]
    
    if not files:
        print("Không có file nào để trích xuất.")
        return

    # Dùng ExcelWriter để lưu nhiều sheet
    with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
        for i, file_name in enumerate(files):
            file_path = os.path.join(pdf_dir, file_name)
            print(f"Đang trích xuất: {file_name}")
            extracted_data = []

            if file_name.lower().endswith('.pdf'):
                extracted_data = extract_tables_from_pdf(file_path)
            elif file_name.lower().endswith('.docx'):
                extracted_data = extract_tables_from_docx(file_path)

            if extracted_data:
                df = pd.DataFrame(extracted_data)
                
                # Tên sheet giới hạn 31 ký tự, thay thế các ký tự không hợp lệ
                sheet_name = file_name[:25] + f"_{i}"
                invalid_chars = ['*', ':', '?', '[', ']', '/', '\\']
                for char in invalid_chars:
                    sheet_name = sheet_name.replace(char, '_')
                
                df.to_excel(writer, sheet_name=sheet_name, index=False, header=False)
                print(f" -> Đã trích xuất {len(extracted_data)} dòng vào sheet {sheet_name}")
            else:
                print(" -> Không tìm thấy bảng nào.")

    print(f"\nHoàn tất! Kết quả được lưu tại: {output_excel}")

if __name__ == '__main__':
    main()

import pandas as pd
import json
import sys

def convert(json_file, excel_file):
    # Đọc file json
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Chuẩn bị dữ liệu để đưa vào DataFrame
    rows = []
    for item in data:
        row = {
            'Tiêu đề': item.get('title', ''),
            'Ngày': item.get('date', ''),
            'Loại': item.get('type', ''),
            'Trang': item.get('page', ''),
            'URL Bài viết': item.get('article_url', ''),
            'Nội dung': item.get('content', ''),
        }
        
        # Xử lý phần file đính kèm (chuyển list thành chuỗi cách nhau bởi dấu phẩy hoặc xuống dòng)
        attachments = item.get('attachments', [])
        row['File đính kèm'] = '\n'.join(attachments) if attachments else ''
        
        # Xử lý phần bảng (tạm thời gom thành chuỗi JSON để không bị lỗi cấu trúc)
        tables = item.get('tables', [])
        if tables and tables[0]:
            row['Dữ liệu Bảng (JSON)'] = json.dumps(tables, ensure_ascii=False)
        else:
            row['Dữ liệu Bảng (JSON)'] = ''
            
        rows.append(row)
        
    # Tạo DataFrame và xuất ra Excel
    df = pd.DataFrame(rows)
    df.to_excel(excel_file, index=False)

if __name__ == '__main__':
    if len(sys.argv) == 3:
        convert(sys.argv[1], sys.argv[2])
    else:
        print("Usage: python json_to_excel_gen.py input.json output.xlsx")

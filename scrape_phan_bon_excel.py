import asyncio
from playwright.async_api import async_playwright
import pandas as pd
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print("Đang tải trang masophanbon.com...")
        await page.goto('https://www.masophanbon.com/', timeout=60000)
        await page.wait_for_load_state('networkidle')
        
        # Tìm frame chứa google.script.run
        target_frame = None
        for frame in page.frames:
            try:
                has_gsr = await frame.evaluate("typeof google !== 'undefined' && typeof google.script !== 'undefined' && typeof google.script.run !== 'undefined'")
                if has_gsr:
                    target_frame = frame
                    break
            except:
                pass

        if not target_frame:
            print("Không tìm thấy iframe chứa Google Apps Script!")
            await browser.close()
            return

        print("Đã kết nối được API. Đang yêu cầu TOÀN BỘ dữ liệu (ma='')...")
        try:
            # Lấy toàn bộ dữ liệu
            result = await target_frame.evaluate('''
                () => {
                    return new Promise((resolve, reject) => {
                        google.script.run
                            .withSuccessHandler(res => resolve(res))
                            .withFailureHandler(err => reject(err))
                            .searchPhanBon('[{"ten":"","ma":""}]');
                    });
                }
            ''')
            
            if isinstance(result, list):
                print(f"Đã tải về thành công {len(result)} bản ghi!")
                
                # Chuyển đổi sang DataFrame
                df = pd.DataFrame(result)
                
                # Đổi tên cột cho dễ đọc theo phân tích của người dùng
                rename_map = {
                    'A': 'Mã số',
                    'B': 'Tên phân bón',
                    'C': 'Số quyết định',
                    'D': 'Thời hạn hiệu lực',
                    'E': 'Loại phân bón',
                    'F': 'Cách bón',
                    'G': 'Thành phần',
                    'AJ': 'Hướng dẫn sử dụng',
                    'AK': 'Thông tin doanh nghiệp'
                }
                df.rename(columns=rename_map, inplace=True)
                
                # Xuất ra Excel
                output_file = r'e:\caodata\caodata\phan_bon.xlsx'
                df.to_excel(output_file, index=False)
                print(f"Đã lưu toàn bộ dữ liệu ra file Excel tại: {output_file}")
            else:
                print("Kết quả trả về không phải là một danh sách (list).")
                print(str(result)[:1000])

        except Exception as e:
            print(f"Lỗi khi gọi API: {e}")

        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())

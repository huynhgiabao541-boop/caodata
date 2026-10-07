import os
import urllib.parse
import requests
import sys
import urllib3

urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8')

def download_files(file_list_path, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(file_list_path, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip()]

    for raw_url in urls:
        # Xử lý URL
        parsed = urllib.parse.urlparse(raw_url)
        encoded_path = urllib.parse.quote(parsed.path)
        url = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, encoded_path, parsed.params, parsed.query, parsed.fragment))
        
        file_name = urllib.parse.unquote(os.path.basename(parsed.path))
        file_path = os.path.join(output_dir, file_name)

        print(f"Downloading: {file_name}")
        try:
            response = requests.get(url, stream=True, verify=False, timeout=30)
            if response.status_code == 200:
                with open(file_path, 'wb') as out_file:
                    for chunk in response.iter_content(chunk_size=8192):
                        out_file.write(chunk)
                print(f" -> Success: {file_name}")
            else:
                print(f" -> Error {response.status_code}: Cannot download")
        except Exception as e:
            print(f" -> Error: {str(e)}")

if __name__ == '__main__':
    download_files(r'e:\caodata\caodata\thuocBVTV.txt', r'e:\caodata\caodata\thuocBVTV_pdfs')

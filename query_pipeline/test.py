import requests, os, time, io

def download_pdf(url, save_path):
    # if os.path.exists(save_path): return
    retry = 3
    while retry > 0:        
        try:                
            print(f"Downloading paper {url} to {save_path}")
            # Download the file
            response = requests.get(url, timeout=600, stream=True)
            print(f"Downloading paper {url} to {save_path}")
            response.raise_for_status()
            print(f"Downloading paper {url} to {save_path}")
            
            # Save to file
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            file_size = os.path.getsize(save_path) / (1024 * 1024)  # Size in MB
            print(f"Successfully downloaded to: {save_path} ({file_size:.2f} MB)")
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"Error downloading paper: {e}. Retry: {retry}")
            if isinstance(e, requests.exceptions.HTTPError) and response.status_code in [400, 401, 403, 404]: return
            retry -= 1
            if retry > 0: time.sleep(2)
        except Exception as e:
            retry -= 1
            print(f"Unknown error downloading paper: {e}. Retry: {retry}")
            if retry > 0: time.sleep(1)


def download_pdf_to_memory(url):
    """下载 PDF 文件"""
    while retry > 0:        
        try:                
            # Download the file
            response = requests.get(url, timeout=600, stream=True)
            response.raise_for_status()
            return io.BytesIO(response.content)            
        except requests.exceptions.RequestException as e:
            if isinstance(e, requests.exceptions.HTTPError) and response.status_code in [400, 401, 403, 404]: return
            retry -= 1
            print(f"Error downloading paper: {e}. Retry: {retry}")
            if retry > 0: time.sleep(2)
        except Exception as e:
            retry -= 1
            print(f"Unknown error downloading paper: {e}. Retry: {retry}")
            if retry > 0: time.sleep(1)


def parse_with_grobid(pdf):
    """通过 GROBID 解析 PDF（带重试）"""
    try:      
        files = {"input": pdf}
        response = requests.post("http://localhost:8070/api/processFulltextDocument", files=files)
        response.raise_for_status()
        return response.text                
    except KeyboardInterrupt:
        raise
    except Exception as e:
        print(f"GROBID unexpected error: {e}")
        
# url = "https://pubs.acs.org/doi/pdf/10.1021/acscentsci.8b00551"
inputs = "sample.pdf"
# download_pdf(url, inputs)
# pdf = download_pdf_to_memory(url)
# inputs = ("paper.pdf", pdf, "application/pdf")
text = parse_with_grobid(inputs)

import os
import requests
import zipfile
from tqdm import tqdm

def download_file(url, dest_path):
    if os.path.exists(dest_path):
        print(f"File already exists: {dest_path}")
        return
    
    print(f"Downloading {url} to {dest_path}...")
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    
    with open(dest_path, 'wb') as file, tqdm(
        desc=os.path.basename(dest_path),
        total=total_size,
        unit='iB',
        unit_scale=True,
        unit_divisor=1024,
    ) as bar:
        for data in response.iter_content(chunk_size=1024):
            size = file.write(data)
            bar.update(size)

def unzip_file(zip_path, extract_to):
    print(f"Extracting {zip_path} to {extract_to}...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)

if __name__ == "__main__":
    # Define models
    models = [
        {
            "url": "https://lab.ndl.go.jp/dataset/ndlkotensekiocr/trocr/model-ver2.zip",
            "dest": "src/text_kotenseki_recognition/model-ver2.zip",
            "extract_to": "src/text_kotenseki_recognition/"
        },
        {
            "url": "https://lab.ndl.go.jp/dataset/ndlkotensekiocr/layoutmodel/ndl_kotenseki_layout_ver3.pth",
            "dest": "src/ndl_kotenseki_layout/models/ndl_kotenseki_layout_ver3.pth",
            "extract_to": None
        }
    ]
    
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    for model in models:
        dest_path = os.path.join(project_root, model["dest"])
        download_file(model["url"], dest_path)
        
        extract_to = model.get("extract_to")
        if extract_to:
            extract_path = os.path.join(project_root, extract_to)
            unzip_file(dest_path, extract_path)
            # Optionally remove the zip file after extraction
            # os.remove(dest_path)

    print("Model downloads and extraction complete.")

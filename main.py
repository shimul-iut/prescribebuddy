import os
import base64
from PIL import Image, ImageDraw, ImageFont
import anthropic
import shutil
from typing import List, Dict, Union
from dotenv import load_dotenv
import fitz
from prompt import system_prompt
# Load environment variables from .env file
load_dotenv()

class PrescribeBuddy:
    
    def __init__(self):
        """Initialize the processor with your Anthropic API key from .env."""
        self.client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        script_dir = os.path.dirname(os.path.abspath(__file__))  # Gets the directory where run.py is located
        dxf_directory = os.path.join(script_dir, "input")
    
        self.input_path = os.path.join(dxf_directory,"prescription.pdf")
        self.output_dir = os.path.join(script_dir,"output")
        
    def pdf_to_images(self, max_file_size_mb=4, initial_dpi=800, max_dimension=8000):
    # Ensure the output directory exists
        print("\n=== Started transforming the Prescription pdf to image ===")

        if not os.path.exists(self.input_path):
            raise FileNotFoundError(f"PDF file not found: {self.input_path}")

    # Ensure the output directory exists
        os.makedirs(self.output_dir, exist_ok=True)

        # Open the PDF file
        pdf_document = fitz.open(self.input_path)
        max_file_size_bytes = max_file_size_mb * 1024 * 1024  # Convert MB to bytes
        image_paths = []

        for page_number in range(len(pdf_document)):
            page = pdf_document[page_number]

        # Start with the initial DPI
            dpi = initial_dpi
            image_name = os.path.splitext(os.path.basename(self.input_path))[0]
            image_path = os.path.join(self.output_dir, image_name+".png")

            while True:
            # Render page to a pixmap at the current DPI
                zoom = dpi / 72  # Scale factor relative to default 72 DPI
                mat = fitz.Matrix(zoom, zoom)
                pixmap = page.get_pixmap(matrix=mat, alpha=False)

                # Check dimensions
                if pixmap.width > max_dimension or pixmap.height > max_dimension:
                    scale_factor = max_dimension / max(pixmap.width, pixmap.height)
                    dpi = int(dpi * scale_factor)
                    continue  # Re-render with adjusted DPI

                # Save the image temporarily
                pixmap.save(image_path)

                # Check file size
                file_size = os.path.getsize(image_path)
                if file_size <= max_file_size_bytes:
                    break  # File size is within the limit
                elif dpi > 50:  # Reduce DPI if size exceeds the limit
                    dpi = int(dpi * 0.8)  # Reduce DPI by 20%
                else:
                    print(f"Warning: Cannot reduce file size below {max_file_size_mb}MB for page {page_number + 1}.")
                    break

            image_paths.append(image_path)

        pdf_document.close()
        return image_paths

    def encode_pdf(self, image_path):
        """Encode an image file to base64 and determine its media type."""

        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
        print("\n=== Encoded the Image ===")
        return encoded_string

    def process_image(self, image_path:str) -> Dict:
        print("\n=== Started transforming the Prescription pdf to image ===")

        """Process images to detect objects and their bounding boxes."""
        encoded_string = self.encode_pdf(image_path)
        content= [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": encoded_string
                }
            },
            {
                "type": "text",
                "text": "Please extract all relevant annotations and legends from the Image Document"
            }
        ]


       
        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=8000,
                system=system_prompt,
                messages=[{
                    "role": "user",
                    "content": content
                }]
            )

            response_text = response.content[0].text
            return response_text

        except Exception as e:
            print(f"Error processing pdf: {str(e)}")
            return None

def delete_folder(folder_path):
    if os.path.exists(folder_path):
        try:
            shutil.rmtree(folder_path)  # Deletes the folder and its contents
            print(f"Folder '{folder_path}' deleted successfully.")
        except Exception as e:
            print(f"Error deleting folder '{folder_path}': {e}")
    else:
        print(f"Folder '{folder_path}' does not exist.")

# Example usage


def main():
    """Process pdf with Claude Vision API"""
    print("\n=== Converting PDF to Image ===")
    
   
    try:
        processor = PrescribeBuddy()
        result = processor.pdf_to_images()
        print("\n=== Starting scanning Image ===")

        if os.path.isdir(result[0]):
            image_path = result[0]  # Assign if it's a directory
            # Additional logic to find matching images in the directory (if needed)
        else:
            # If result[0] is not a directory, treat it as a file path
            image_path = result[0]

            try:
                response = processor.process_image(image_path)
                with open("response.html", "w", encoding="utf-8") as f:
                    f.write(response)
                    
                print ("\n=== Output html is generated ===")  
                
                print ("\n=== Deleting output folder image ===")  
                #optional 
                delete_folder(processor.output_dir)

            except Exception as e:
                print(f"Error processing pdf: {str(e)}")
                return None

    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()

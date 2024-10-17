import os
import shutil
import numpy as np
from PIL import Image

split_path = r"images"
# List of possible color channels in tiffsep output
color_channels = ["Cyan", "Magenta", "Yellow", "Black"]

def clear_path(path):
    # remove the whole Dictionary
    if os.path.exists(path):
        shutil.rmtree(path)
    # make the Dictionary in the place with same name
    os.mkdir(path)

def organize_tiff():
    # Create color-specific folders and move files
    for color in color_channels:
        # Create a directory for each color if it doesn’t already exist
        color_folder = os.path.join(split_path, color)
        os.makedirs(color_folder, exist_ok=True)

        # Move files that match the color channel to the respective folder
        for file_name in os.listdir(split_path):
            if color in file_name:
                shutil.move(os.path.join(split_path, file_name), color_folder)

def split_page(pdf_path):
    # clear the Dictionary for images to stor
    clear_path(split_path)
    # use ghost-scrip to split each page of pdf into a separate image with the 4 main color of printing
    os.system(fr'gswin64c -sDEVICE=tiffsep -o {split_path}\p_%d_%%c.tiff -f {pdf_path}')
    # to organize the tiff file into separate folders
    organize_tiff()

def calculate_all_color():
    colo = {}
    # process each color separately
    for color in color_channels:
        # use the calculate_coverage_for_color to get the average ink usage in all pages
        colo.update({color: calculate_coverage_for_color(os.path.join(split_path, color))})
    return colo

def calculate_coverage_for_color(path_images):
    total_intensity = 0
    max_intensity = 0

    for file_path in os.listdir(path_images):
        with Image.open(os.path.join(path_images, file_path)) as img:
            # Convert the image to a numpy array for efficient processing
            img_data = np.array(img)
            # Theoretical maximum intensity if all pixels were at maximum color (0 intensity)
            max_intensity += img_data.size * 255
            # Calculate the color intensity (inverse of pixel brightness)
            total_intensity += np.sum(255 - img_data)  # 255 - pixel value gives "color intensity"

    # Calculate coverage as a percentage of the total intensity to max possible intensity
    # and format it into float number with 2 decimal place
    return "{:0.2f}".format((total_intensity / max_intensity) * 100 if max_intensity > 0 else 0)

def make_grayscale(pdf_path):
    if not os.path.exists(r"grayscale"):
        os.mkdir(r"grayscale")
    os.system(fr"gswin64c -sDEVICE=pdfwrite -dNOPAUSE -dBATCH -dSAFER -sColorConversionStrategy=Gray -dProcessColorModel=/DeviceGray -sOutputFile=grayscale\gray.pdf {pdf_path}")

def run(pdf_path):
    split_page(pdf_path)
    color = calculate_all_color()
    make_grayscale(pdf_path)
    split_page(r"grayscale\gray.pdf")
    black = calculate_all_color()
    print("color cov :\n" , color)
    print("black cov :\n" , black)
    clear_path(split_path)

path = r"USE/YOUR/OWN/PATH"
run(path)
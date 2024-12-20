import logging
import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pypdf
from PIL import Image

split_path = r"images"
# List of possible color channels in tiffsep output
color_channels = ["Cyan", "Magenta", "Yellow", "Black"]
log_file = r"log.txt"

def setup_logger():
    if os.path.exists(log_file):
        os.remove(log_file)
    with open(log_file, "a") as f:
        f.write("file is Created\n")

    logger_new = logging.getLogger('GhostscriptLogger')
    logger_new.setLevel(logging.INFO)

    # File handler for logging
    handler = logging.FileHandler(log_file, mode='a')
    handler.setLevel(logging.INFO)

    # Formatter for the logs
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger_new.info("logger started")

    # Add handler to logger
    if not logger_new.hasHandlers():
        logger_new.addHandler(handler)

    return logger_new
logger = setup_logger()

def clear_path(path_clear):
    # remove the whole Dictionary
    if os.path.exists(path_clear):
        shutil.rmtree(path_clear)
    # make the Dictionary in the place with same name
    os.mkdir(path_clear)

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
    """Splits each page of the PDF into separate color-separated images."""
    # Clear the dictionary for storing images
    clear_path(split_path)
    logger.info(f"Started splitting for {pdf_path}")
    try:
        # Get the total number of pages
        page_count = get_pdf_page_count(pdf_path)
        # Use parallel processing to run Ghostscript for each page
        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(split_single_page, pdf_path, page) for page in range(1, page_count + 1)]
            for future in futures:
                future.result()  # Ensure all tasks complete
        logger.info("Split Tiffs successfully created")
    except Exception as e:
        logger.error(f"Error splitting pdf {pdf_path}: {e}")
    finally:
        # Organize the TIFF files into separate folders by color
        organize_tiff()
        logger.info("Split completed and organized successfully.")

def get_pdf_page_count(pdf_path):
    """Returns the number of pages in the PDF."""
    pdf_reader = pypdf.PdfReader(pdf_path)
    return len(pdf_reader.pages)

def split_single_page(pdf_path, page):
    """Processes a single page by splitting it into color-separated TIFF images."""
    command = fr'gswin64c -q -sDEVICE=tiffsep -dFirstPage={page} -dLastPage={page} -o {split_path}\p_{page}_%%c.tiff -f {pdf_path}'

    try:
        # Execute the Ghostscript command and capture the output
        os.system(command)
        # Log success after command completes
        logger.info(f"Page {page} split into tiff successfully.")
    except Exception as e:
        # Log any exceptions that occur
        logger.error(f"Error processing page {page}: {e}")

def calculate_all_color():
    colo = {}
    # process each color separately
    for color in color_channels:
        # use the calculate_coverage_for_color to get the average ink usage in all pages
        colo.update({color: float(calculate_coverage_for_color(os.path.join(split_path, color)))})
        logger.info(f"Color {color} calculated successfully with a coverage of {colo[color]}")
    clear_path(split_path)
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

def convert_page_to_grayscale(pdf_path, page_number, output_dir):
    """Converts a single page to grayscale and saves it as a separate PDF."""
    temp_pdf_path = os.path.join(output_dir, f"page_{page_number}.pdf")
    gs_command = [
        "gswin64c", "-sDEVICE=pdfwrite", "-dNOPAUSE", "-dBATCH",
        "-sColorConversionStrategy=Gray", "-dProcessColorModel=/DeviceGray",
        "-dDownsampleColorImages=true", "-dColorImageResolution=600",
        f"-dFirstPage={page_number}", f"-dLastPage={page_number}",
        f"-sOutputFile={temp_pdf_path}", pdf_path
    ]

    try:
        subprocess.run(gs_command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logger.info(f"Page {page_number} grayscale successfully.")
        return page_number, temp_pdf_path  # Return the page number to keep track of order
    except subprocess.CalledProcessError as e:
        logger.error(f"Error converting page {page_number} to grayscale: {e}")
        return page_number, None

def combine_pdfs(page_paths, output_pdf_path):
    """Combines all individual page PDFs into a single PDF."""
    try:
        valid_paths = [path_pdf for _, path_pdf in sorted(page_paths) if path_pdf is not None]
        if not valid_paths:
            logger.error(f"No valid paths were found for page {page_paths}")
            return

        gs_command = ["gswin64c", "-sDEVICE=pdfwrite", "-dNOPAUSE", "-dBATCH",
                      "-sOutputFile=" + output_pdf_path] + valid_paths
        subprocess.run(gs_command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logger.info("page PDFs successfully combined.")
    except Exception as e:
        logger.error(f"Error combining page PDFs: {e}")

def make_grayscale(pdf_path):
    # Create output directory for temporary grayscale pages
    output_dir = "grayscale_pages"
    os.makedirs(output_dir, exist_ok=True)

    logger.info(f"Started grayscale conversion for {pdf_path}")
    try:
        # Get total number of pages using Ghostscript
        total_pages = get_pdf_page_count(pdf_path)

        # Use limited parallel processing to convert each page to grayscale
        grayscale_page_paths = []
        with ThreadPoolExecutor() as executor:  # Adjust worker count as needed
            futures = [
                executor.submit(convert_page_to_grayscale, pdf_path, page_num + 1, output_dir)
                for page_num in range(total_pages)
            ]

            # Collect the results and maintain the page order
            for future in futures:
                page_number, result = future.result()
                if result is not None:
                    grayscale_page_paths.append((page_number, result))
                else:
                    logger.error(f"Error converting page {page_number} to grayscale.")

        # Combine all grayscale pages into a single PDF, ordered by page number
        output_pdf_path = os.path.join("grayscale", "gray.pdf")
        os.makedirs("grayscale", exist_ok=True)
        combine_pdfs(grayscale_page_paths, output_pdf_path)

        logger.info(f"Grayscale PDF successfully created: {output_pdf_path}")

    except Exception as e:
        logger.error(f"Error during grayscale conversion: {e}")

    finally:
        # Clean up temporary files
        clear_path(r"grayscale_pages")
        logger.info("Grayscale conversion completed and temporary files cleaned up.")

def calculate_color_coverage(pdf_path):
    split_page(pdf_path)
    color = calculate_all_color()
    page = get_pdf_page_count(pdf_path)
    for colo in color.keys():
        color[colo] = float("{:0.2f}".format(color[colo] * page))
    logger.info(f"PDF color Coverage calculated successfully.\nCoverage : {color}")
    return color

def calculate_grayscale_coverage(pdf_path):
    make_grayscale(pdf_path)
    split_page(r"grayscale/gray.pdf")
    black = calculate_all_color()
    page = get_pdf_page_count(pdf_path)
    black = black["Black"] * page
    logger.info(f"PDF grayscale Coverage calculated successfully.\nCoverage : {black}")
    return black
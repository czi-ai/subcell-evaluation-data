import os
import cv2
import numpy as np
import tifffile

# Naive approach, the code expects all input images to reside in a folder and it will save the results the output_folder
input_folder = "./allencell"
output_folder = "./result/allencell"
# Simple metadata file to parse later on
metadata_file = "metadata.csv"

# Pixel to micron values for the HPA dataset and for OpenCell dataset. Used to resize the crop later on
pixel_micron_HPA = 0.0800885
pixel_micron_AllenCell = 0.10833
# Final crop size
crop_size = 640
crop_size_hf = int(crop_size / 2)


os.makedirs(output_folder, exist_ok=True)
mf = open(os.path.join(output_folder, metadata_file), "w")
# Metadata headers
mf.write("image,orig_img_width,orig_img_height,resz_image,resz_img_width,resz_img_height\n")

for input_image in os.listdir(input_folder):
    # Reading the tif file as numpy array
    tif_img = tifffile.imread(os.path.join(input_folder, input_image))

    # Calculating the z projection of the image and trasposing the numpy array to match image dimensions
    max_proj = np.max(tif_img, axis=0).transpose(1, 2, 0)
    cv2.imwrite(os.path.join(output_folder, input_image).replace(".tif", "_proj.png"), np.uint16(max_proj))

    # Saving the original crop data for the current image
    crop_data = input_image + "," + str(len(max_proj[0])) + "," + str(len(max_proj))

    # Now we generate the crops for the resized images to the HPA pixel to micron resolution
    max_proj = cv2.resize(max_proj, None, fx=pixel_micron_AllenCell / pixel_micron_HPA, fy=pixel_micron_AllenCell / pixel_micron_HPA)
    # Creating an empty crop
    crop = np.zeros((crop_size, crop_size, 3))
    # Getting matching center coordinates of the resized image and the cropped image
    center_y = min(crop_size_hf, int(len(max_proj) / 2))
    center_x = min(crop_size_hf, int(len(max_proj[0]) / 2))
    # Copying the sliced crop from the resized image
    crop[(crop_size_hf - center_y):(crop_size_hf + center_y), (crop_size_hf - center_x):(crop_size_hf + center_x)] = max_proj[(int(len(max_proj) / 2) - center_y):(int(len(max_proj) / 2) + center_y),(int(len(max_proj[0]) / 2) - center_x):(int(len(max_proj[0]) / 2) + center_x)]

    # Saving the crop of the resized image
    resz_image_fn = os.path.join(output_folder, input_image).replace(".tif", "_crop_resized.png")
    cv2.imwrite(resz_image_fn, np.uint16(crop))
    # Saving the resized crop data for the current image
    crop_data = crop_data + "," + os.path.basename(resz_image_fn) + "," + str(len(max_proj[0])) + "," + str(len(max_proj))

    # Writing the current image crops information in the metadata file
    mf.write(crop_data + "\n")

mf.close()
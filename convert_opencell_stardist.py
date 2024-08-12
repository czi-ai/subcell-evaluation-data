import os
import cv2
import numpy as np
from skimage.measure import regionprops
from skimage.morphology import remove_small_objects
from skimage.segmentation import clear_border, relabel_sequential
from stardist.models import StarDist2D
import tifffile


# Naive approach, the code expects all input images to reside in a folder and it will save the results the output_folder
input_folder = "./opencell"
output_folder = "./result/opencell"
# Simple metadata file to parse later on
metadata_file = "metadata.csv"

# Segmented nuclei with less area/pixels than this will be discarded
micro_nuclei_max_area = 2500
# Pixel to micron values for the HPA dataset and for OpenCell dataset. Used to resize the crop later on
pixel_micron_HPA = 0.0800885
pixel_micron_OpenCell = 0.206349
# Final crop size
crop_size_orig = 256
crop_size_orig_hf = int(crop_size_orig / 2)
crop_size_resized = 640
crop_size_resized_hf = int(crop_size_resized / 2)

model = StarDist2D.from_pretrained('2D_versatile_fluo')
os.makedirs(output_folder, exist_ok=True)
mf = open(os.path.join(output_folder, metadata_file), "w")
# Metadata headers
mf.write("image,cell_id,orig_img_width,orig_img_height,orig_center_x,orig_center_y,orig_nuc_area,resz_img_width,resz_img_height,resz_center_x,resz_center_y,resz_nuc_area\n")

for input_image in os.listdir(input_folder):
    crops_data = []
    # Reading the tif file as numpy array
    tif_img = tifffile.imread(os.path.join(input_folder, input_image))

    np_img_prot = tif_img[1]
    #imsave(os.path.join(output_folder, input_image).replace("_proj.tif", "_prot.png"), np.uint16(np_img_prot))

    np_img_nuc = tif_img[0]
    #imsave(os.path.join(output_folder, input_image).replace("_proj.tif", "_nuc.png"), np.uint16(np_img_nuc))

    # Normalizing image (Stardist requirement)
    np_img_nuc_norm = (np_img_nuc - np.amin(np_img_nuc)) / (np.amax(np_img_nuc) - np.amin(np_img_nuc))
    # Running Stardist segmentation to obtain a labeled image with segmented nuclei
    nuc_labels, _ = model.predict_instances_big(np_img_nuc_norm, axes='YX', block_size=512, min_overlap=64)
    # Removing segmented nuclei with less area/pixels than micro_nuclei_max_area
    nuc_labels = remove_small_objects(nuc_labels, micro_nuclei_max_area)
    # Removing segmented nuclei touching the image borders
    nuc_labels = clear_border(nuc_labels)
    # Relabeling nuclei so their id is sequential
    nuc_labels = relabel_sequential(nuc_labels)[0]
    #cv2.imwrite(os.path.join(output_folder, input_image).replace("_proj.tif", "_nuc_labels.png"), np.uint8(nuc_labels))


    # Iterating over all segmented nuclei
    for curr_crop in regionprops(nuc_labels):
        # Creating an empty crop per segmented nuclei
        crop = np.zeros((crop_size_orig, crop_size_orig, 3))
        # Getting matching center coordinates of the original images and the cropped image
        center_image = [int(curr_crop.centroid[0]), int(curr_crop.centroid[1])]
        crop_left = max(0, center_image[1] - crop_size_orig_hf)
        crop_top = max(0, center_image[0] - crop_size_orig_hf)
        crop_right = min(len(np_img_prot[0]), center_image[1] + crop_size_orig_hf)
        crop_bottom = min(len(np_img_prot), center_image[0] + crop_size_orig_hf)
        # Copying the sliced crop from the original image
        crop[(crop_size_orig_hf - (center_image[0] - crop_top)):(crop_size_orig_hf + (crop_bottom - center_image[0])), (crop_size_orig_hf - (center_image[1] - crop_left)):(crop_size_orig_hf + (crop_right - center_image[1])), 1] = np_img_prot[crop_top:crop_bottom, crop_left:crop_right]
        crop[(crop_size_orig_hf - (center_image[0] - crop_top)):(crop_size_orig_hf + (crop_bottom - center_image[0])), (crop_size_orig_hf - (center_image[1] - crop_left)):(crop_size_orig_hf + (crop_right - center_image[1])), 0] = np_img_nuc[crop_top:crop_bottom, crop_left:crop_right]

        # Saving the crop of the original image
        cv2.imwrite(os.path.join(output_folder, input_image).replace("_proj.tif", "_crop_" + str(curr_crop.label) + ".png"), np.uint16(crop))
        # Saving the original crops data for the current image
        crops_data.append(input_image + "," + str(curr_crop.label) + "," + str(len(np_img_nuc[0])) + "," + str(len(np_img_nuc)) + "," + str(center_image[1]) + "," + str(center_image[0]) + "," + str(int(curr_crop.area)))


    # Now we generate the crops for the resized images to the HPA pixel to micron resolution
    np_img_prot = cv2.resize(np_img_prot, None, fx=pixel_micron_OpenCell / pixel_micron_HPA, fy=pixel_micron_OpenCell / pixel_micron_HPA)
    np_img_nuc = cv2.resize(np_img_nuc, None, fx=pixel_micron_OpenCell / pixel_micron_HPA, fy=pixel_micron_OpenCell / pixel_micron_HPA)
    nuc_labels = cv2.resize(nuc_labels, None, fx=pixel_micron_OpenCell / pixel_micron_HPA, fy=pixel_micron_OpenCell / pixel_micron_HPA, interpolation = cv2.INTER_NEAREST)
    # Iterating over all segmented nuclei
    for curr_crop in regionprops(nuc_labels):
        # Creating an empty crop per segmented nuclei
        crop = np.zeros((crop_size_resized, crop_size_resized, 3))
        # Getting matching center coordinates of the original images and the cropped image
        center_image = [int(curr_crop.centroid[0]), int(curr_crop.centroid[1])]
        crop_left = max(0, center_image[1] - crop_size_resized_hf)
        crop_top = max(0, center_image[0] - crop_size_resized_hf)
        crop_right = min(len(np_img_prot[0]), center_image[1] + crop_size_resized_hf)
        crop_bottom = min(len(np_img_prot), center_image[0] + crop_size_resized_hf)
        # Copying the sliced crop from the resized image
        crop[(crop_size_resized_hf - (center_image[0] - crop_top)):(crop_size_resized_hf + (crop_bottom - center_image[0])), (crop_size_resized_hf - (center_image[1] - crop_left)):(crop_size_resized_hf + (crop_right - center_image[1])), 1] = np_img_prot[crop_top:crop_bottom, crop_left:crop_right]
        crop[(crop_size_resized_hf - (center_image[0] - crop_top)):(crop_size_resized_hf + (crop_bottom - center_image[0])), (crop_size_resized_hf - (center_image[1] - crop_left)):(crop_size_resized_hf + (crop_right - center_image[1])), 0] = np_img_nuc[crop_top:crop_bottom, crop_left:crop_right]

        # Saving the crop of the resized image
        cv2.imwrite(os.path.join(output_folder, input_image).replace("_proj.tif", "_crop_" + str(curr_crop.label) + "_resized.png"), np.uint16(crop))
        # Adding the resized crops data for the current image
        crops_data[curr_crop.label - 1] = crops_data[curr_crop.label - 1] + "," + str(len(np_img_nuc[0])) + "," + str(len(np_img_nuc)) + "," + str(center_image[1]) + "," + str(center_image[0]) + "," + str(int(curr_crop.area))

    # Writing the current image crops information in the metadata file
    mf.write("\n".join(crops_data) + "\n")

mf.close()

import numpy as np
import pandas as pd

# Load metadata generated by our workflow
meta_open = pd.read_csv("opencell.metadata.csv")

# Parse out gene name and Ensembl ID from file names
meta_open[["gene_name", "ensembl_id"]] = meta_open["image"].str.split("_", expand = True)[[1, 2]]

# Construct the output metadata table
meta_open_final = pd.DataFrame({
    "top": meta_open["resz_center_y"] - 640/2,
    "left": meta_open["resz_center_x"] - 640/2,
    "width": 640,
    "height": 640,
    "id": meta_open["image"].str.replace("proj.tif","") + meta_open["cell_id"].astype(str),
    "location": np.nan,
    "location_code": np.nan,
    "locations": np.nan,
    "gene_names": meta_open["gene_name"],
    "ensembl_ids": meta_open["ensembl_id"],
    "atlas_name": "HEK293T",
    "ImageWidth": meta_open["resz_img_width"],
    "ImageHeight": meta_open["resz_img_height"],
    "target": np.nan,
    "image_id": meta_open["image"].str.replace("_proj.tif",""),
    "cell_id": meta_open["cell_id"],
    "nucleus_area": meta_open["resz_nuc_area"],
    "cell_area": np.nan,
    "resized_image_name": np.nan   # TO DO: add this column
})


meta_open_final.to_csv("opencell.metadata.formatted.csv", index=False)
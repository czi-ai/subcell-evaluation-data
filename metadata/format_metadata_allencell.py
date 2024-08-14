import numpy as np
import pandas as pd


# Upstream metadata from https://github.com/AllenCell/cvapipe_analysis 
# Only using the columns with IDs: csvcut -c 1,3,9 manifest.csv > manifest_IDs.csv
meta_allen_upstream = pd.read_csv("manifest_IDs.csv")
# Create a column to store image name without folder name
meta_allen_upstream["image"] = meta_allen_upstream["crop_raw"].str.replace("crop_raw/", "")

# One of the labeled gene HIST1H2BJ is not standard gene name
# Change it to standard name H2BC11
# See https://www.allencell.org/cell-catalog.html line 61
# https://www.ncbi.nlm.nih.gov/gene/8970
meta_allen_upstream["gene_name"] = meta_allen_upstream["structure_name"].str.replace("HIST1H2BJ", "H2BC11")

# Add Ensembl ID by matching gene name
# Load conversion table from https://www.ensembl.org/biomart/martview Ensembl Genes 112
gene_id = pd.read_table("biomart_export_ensembl112.tsv")

meta_allen_upstream_ensembl = meta_allen_upstream.merge(gene_id, how="left", left_on="gene_name", right_on="Gene name")


# Load metadata generated by our workflow
# Use the tables above to find matching Ensembl ID
meta_allen = pd.read_csv("allencell.metadata.csv").merge(meta_allen_upstream_ensembl, how="left", on="image")

# Print structures that did not find matching Ensembl ID
# AAVS1 is not a protein target https://www.ncbi.nlm.nih.gov/gene/17
no_ensemble_id = meta_allen[meta_allen["Gene stable ID"].isna()]

print("These labeled structures do not have Ensembl IDs")
print(no_ensemble_id["gene_name"].unique())



# Construct the output metadata table
meta_allen_final = pd.DataFrame({
    "top": 0,
    "left": 0,
    "width": 640,
    "height": 640,
    "id": meta_allen["image"].str.replace("_raw.ome.tif",""),
    "location": np.nan,
    "location_code": np.nan,
    "locations": np.nan,
    "gene_names": meta_allen["gene_name"],
    "ensembl_ids": meta_allen["Gene stable ID"],
    "atlas_name": "WTC-11",
    "ImageWidth": meta_allen["resz_img_width"],
    "ImageHeight": meta_allen["resz_img_height"],
    "target": np.nan,
    "image_id": meta_allen["image"].str.replace("_raw.ome.tif",""),
    "cell_id": 1,
    "nucleus_area": np.nan,
    "cell_area": np.nan,
    "resized_image_name": np.nan   # TO DO: add this column
})

meta_allen_final.to_csv("allencell.metadata.formatted.csv", index=False)
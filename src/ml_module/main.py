from PIL import Image
from src.flask_app.drive_utils import upload_file
from src.ml_module.utils import *
import numpy as np
import os
from src.ml_module.pipeline import HumanClothesDetectionPipeline
import cv2

# Folder IDs for Google Drive
DRIVE_FOLDERS = {
    "FULL": "1H66qHlVz4idI-gMPVZi79hf7SGu6h_lD",
    "HEAD": "1OavV3D6tBao6KG13QjPQH4r3PI5TSv3A",
    "PANTS": "1IDRD1B5mVN-Oo6HimMsM49zWlCbI1Wnu",
    "TOP": "16BKpECjxVN_N7HTtQJoaqQkCKnjmH1zz",
}


def service_model(filename, is_full_image=False):
    image = cv2.imread(filename, cv2.IMREAD_COLOR)

    if is_full_image:
        # Upload the full image to the 'full_image' folder
        folder_id = DRIVE_FOLDERS["full_image"]
        upload_file(filename, filename, folder_id)
        return {"message": "Full image uploaded successfully"}

    # Load the model and preprocessor
    pipe = HumanClothesDetectionPipeline()

    # Generate the predictions
    human, preds = pipe(filename)

    # Sort the predictions by area size
    preds.sort(key=lambda x: calculate_area(x['box']), reverse=True)

    # Generate for each category and select the highest
    final_predictions = finalize_predictions(preds)

    # Correct the proportions of the detections
    corrected_predictions = correct_clothing_bounding_boxes(human.values(), final_predictions)

    # Existing logic to process the image...
    meta_data_list = []
    for i, key in enumerate(corrected_predictions.keys()):
        if corrected_predictions[key] is None:
            continue

        try:
            for bound in corrected_predictions[key]['box'].keys():
                corrected_predictions[key]['box'][bound] = int(corrected_predictions[key]['box'][bound])

            xmin, ymin, xmax, ymax = corrected_predictions[key]['box'].values()

            cropped_image = image[ymin:ymax, xmin:xmax, :]
            cropped_file_name = filename[:-4] + f"_{i}.jpg"
            cv2.imwrite(cropped_file_name, cropped_image)

            # Add folder destination based on clothing type
            clothing_type = corrected_predictions[key]['label']
            folder_id = FOLDER_IDS.get(clothing_type, FOLDER_IDS["full"])

            # Save the metadata
            meta_data_list.append({
                'isLiked': False,
                'clothingType': clothing_type,
                'length': ymax - ymin,
                'width': xmax - xmin,
                'file_name': cropped_file_name,
                'folder_id': folder_id
            })
        except Exception as e:
            print(f'Encountered error {e} while cropping, continuing...')

    return meta_data_list
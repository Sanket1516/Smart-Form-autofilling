# OCR models

English PP-OCR models used by the default OCR engine (`OCR_ENGINE=rapidocr`):

| File | Source |
|---|---|
| `en_PP-OCRv3_det_infer.onnx` | PaddleOCR `en_PP-OCRv3_det_infer`, converted with paddle2onnx 1.2.11 (opset 11) |
| `en_PP-OCRv4_rec_infer.onnx` | PaddleOCR `en_PP-OCRv4_rec_infer`, converted with paddle2onnx 1.2.11 (opset 11) |
| `en_dict.txt` | PaddleOCR `ppocr/utils/en_dict.txt` (character list; a space is appended at load) |

These are the same models PaddleOCR 2.x downloads for `lang="en"`. PaddleOCR and its
models are licensed under Apache-2.0 (https://github.com/PaddlePaddle/PaddleOCR).

Re-create them (needs `paddlepaddle<3` and `paddle2onnx==1.2.11`):

    paddle2onnx --model_dir ~/.paddleocr/whl/rec/en/en_PP-OCRv4_rec_infer \
      --model_filename inference.pdmodel --params_filename inference.pdiparams \
      --save_file en_PP-OCRv4_rec_infer.onnx --opset_version 11
    # same for ~/.paddleocr/whl/det/en/en_PP-OCRv3_det_infer

Set `OCR_MODEL_DIR` to load models from another directory.

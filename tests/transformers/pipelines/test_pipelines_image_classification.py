# Copyright 2021 The HuggingFace Team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest

from mindnlp.transformers import (
    MODEL_FOR_IMAGE_CLASSIFICATION_MAPPING,
    PreTrainedTokenizerBase
)
from mindnlp.utils import (
    is_mindspore_available,
    is_vision_available,
)
from mindnlp.transformers.pipelines import ImageClassificationPipeline, pipeline
from mindnlp.utils.testing_utils import (
    is_pipeline_test,
    nested_simplify,
    require_mindspore,
    require_bfloat16,
    require_vision,
    slow,
)

from .test_pipelines_common import ANY


if is_mindspore_available():
    import mindspore
    from mindnlp.core import ops

if is_vision_available():
    from PIL import Image
else:

    class Image:
        @staticmethod
        def open(*args, **kwargs):
            pass


@is_pipeline_test
@require_mindspore
@require_vision
class ImageClassificationPipelineTests(unittest.TestCase):
    model_mapping = MODEL_FOR_IMAGE_CLASSIFICATION_MAPPING

    def get_test_pipeline(
        self,
        model,
        tokenizer=None,
        image_processor=None,
        feature_extractor=None,
        processor=None,
        ms_dtype="float32",
    ):
        image_classifier = ImageClassificationPipeline(
            model=model,
            tokenizer=tokenizer,
            feature_extractor=feature_extractor,
            image_processor=image_processor,
            processor=processor,
            ms_dtype=ms_dtype,
            top_k=2,
        )
        examples = [
            Image.open("./tests/fixtures/tests_samples/COCO/000000039769.png"),
            "http://images.cocodataset.org/val2017/000000039769.jpg",
        ]
        return image_classifier, examples

    def run_pipeline_test(self, image_classifier, examples):
        outputs = image_classifier("./tests/fixtures/tests_samples/COCO/000000039769.png")

        self.assertEqual(
            outputs,
            [
                {"score": ANY(float), "label": ANY(str)},
                {"score": ANY(float), "label": ANY(str)},
            ],
        )

        import datasets

        # we use revision="refs/pr/1" until the PR is merged
        # https://hf.co/datasets/hf-internal-testing/fixtures_image_utils/discussions/1
        dataset = datasets.load_dataset("hf-internal-testing/fixtures_image_utils", split="test", revision="refs/pr/1")

        # Accepts URL + PIL.Image + lists
        outputs = image_classifier(
            [
                Image.open("./tests/fixtures/tests_samples/COCO/000000039769.png"),
                "http://images.cocodataset.org/val2017/000000039769.jpg",
                # RGBA
                dataset[0]["image"],
                # LA
                dataset[1]["image"],
                # L
                dataset[2]["image"],
            ]
        )
        self.assertEqual(
            outputs,
            [
                [
                    {"score": ANY(float), "label": ANY(str)},
                    {"score": ANY(float), "label": ANY(str)},
                ],
                [
                    {"score": ANY(float), "label": ANY(str)},
                    {"score": ANY(float), "label": ANY(str)},
                ],
                [
                    {"score": ANY(float), "label": ANY(str)},
                    {"score": ANY(float), "label": ANY(str)},
                ],
                [
                    {"score": ANY(float), "label": ANY(str)},
                    {"score": ANY(float), "label": ANY(str)},
                ],
                [
                    {"score": ANY(float), "label": ANY(str)},
                    {"score": ANY(float), "label": ANY(str)},
                ],
            ],
        )


    @require_mindspore
    def test_small_model_pt(self):
        small_model = "hf-internal-testing/tiny-random-vit"
        image_classifier = pipeline("image-classification", model=small_model)

        outputs = image_classifier("http://images.cocodataset.org/val2017/000000039769.jpg")
        self.assertEqual(
            nested_simplify(outputs, decimals=4),
            [{"label": "LABEL_1", "score": 0.574}, {"label": "LABEL_0", "score": 0.426}],
        )

        outputs = image_classifier(
            [
                "http://images.cocodataset.org/val2017/000000039769.jpg",
                "http://images.cocodataset.org/val2017/000000039769.jpg",
            ],
            top_k=2,
        )
        self.assertEqual(
            nested_simplify(outputs, decimals=4),
            [
                [{"label": "LABEL_1", "score": 0.574}, {"label": "LABEL_0", "score": 0.426}],
                [{"label": "LABEL_1", "score": 0.574}, {"label": "LABEL_0", "score": 0.426}],
            ],
        )

    def test_custom_tokenizer(self):
        tokenizer = PreTrainedTokenizerBase()

        # Assert that the pipeline can be initialized with a feature extractor that is not in any mapping
        image_classifier = pipeline(
            "image-classification", model="hf-internal-testing/tiny-random-vit", tokenizer=tokenizer
        )

        self.assertIs(image_classifier.tokenizer, tokenizer)

    @require_mindspore
    def test_ms_float16_pipeline(self):
        image_classifier = pipeline(
            "image-classification", model="hf-internal-testing/tiny-random-vit", ms_dtype=mindspore.float16
        )
        outputs = image_classifier("http://images.cocodataset.org/val2017/000000039769.jpg")

        self.assertEqual(
            nested_simplify(outputs, decimals=3),
            [{"label": "LABEL_1", "score": 0.574}, {"label": "LABEL_0", "score": 0.426}],
        )

    @require_mindspore
    @require_bfloat16
    def test_ms_bfloat16_pipeline(self):
        image_classifier = pipeline(
            "image-classification", model="hf-internal-testing/tiny-random-vit", ms_dtype=mindspore.bfloat16
        )
        outputs = image_classifier("http://images.cocodataset.org/val2017/000000039769.jpg")

        self.assertEqual(
            nested_simplify(outputs, decimals=3),
            [{"label": "LABEL_1", "score": 0.574}, {"label": "LABEL_0", "score": 0.426}],
        )

    @slow
    @require_mindspore
    def test_perceiver(self):
        # Perceiver is not tested by `run_pipeline_test` properly.
        # That is because the type of feature_extractor and model preprocessor need to be kept
        # in sync, which is not the case in the current design
        image_classifier = pipeline("image-classification", model="deepmind/vision-perceiver-conv")
        outputs = image_classifier("http://images.cocodataset.org/val2017/000000039769.jpg")
        self.assertEqual(
            nested_simplify(outputs, decimals=4),
            [
                {"score": 0.4385, "label": "tabby, tabby cat"},
                {"score": 0.321, "label": "tiger cat"},
                {"score": 0.0502, "label": "Egyptian cat"},
                {"score": 0.0137, "label": "crib, cot"},
                {"score": 0.007, "label": "radiator"},
            ],
        )

        image_classifier = pipeline("image-classification", model="deepmind/vision-perceiver-fourier")
        outputs = image_classifier("http://images.cocodataset.org/val2017/000000039769.jpg")
        self.assertEqual(
            nested_simplify(outputs, decimals=4),
            [
                {"score": 0.5658, "label": "tabby, tabby cat"},
                {"score": 0.1309, "label": "tiger cat"},
                {"score": 0.0722, "label": "Egyptian cat"},
                {"score": 0.0707, "label": "remote control, remote"},
                {"score": 0.0082, "label": "computer keyboard, keypad"},
            ],
        )

        image_classifier = pipeline("image-classification", model="deepmind/vision-perceiver-learned")
        outputs = image_classifier("http://images.cocodataset.org/val2017/000000039769.jpg")
        self.assertEqual(
            nested_simplify(outputs, decimals=4),
            [
                {"score": 0.3022, "label": "tabby, tabby cat"},
                {"score": 0.2362, "label": "Egyptian cat"},
                {"score": 0.1856, "label": "tiger cat"},
                {"score": 0.0324, "label": "remote control, remote"},
                {"score": 0.0096, "label": "quilt, comforter, comfort, puff"},
            ],
        )

    @slow
    @require_mindspore
    def test_multilabel_classification(self):
        small_model = "hf-internal-testing/tiny-random-vit"

        # Sigmoid is applied for multi-label classification
        image_classifier = pipeline("image-classification", model=small_model)
        image_classifier.model.config.problem_type = "multi_label_classification"

        outputs = image_classifier("http://images.cocodataset.org/val2017/000000039769.jpg")
        self.assertEqual(
            nested_simplify(outputs, decimals=4),
            [{"label": "LABEL_1", "score": 0.5356}, {"label": "LABEL_0", "score": 0.4612}],
        )

        outputs = image_classifier(
            [
                "http://images.cocodataset.org/val2017/000000039769.jpg",
                "http://images.cocodataset.org/val2017/000000039769.jpg",
            ]
        )
        self.assertEqual(
            nested_simplify(outputs, decimals=4),
            [
                [{"label": "LABEL_1", "score": 0.5356}, {"label": "LABEL_0", "score": 0.4612}],
                [{"label": "LABEL_1", "score": 0.5356}, {"label": "LABEL_0", "score": 0.4612}],
            ],
        )

    @slow
    @require_mindspore
    def test_function_to_apply(self):
        small_model = "hf-internal-testing/tiny-random-vit"

        # Sigmoid is applied for multi-label classification
        image_classifier = pipeline("image-classification", model=small_model)

        outputs = image_classifier(
            "http://images.cocodataset.org/val2017/000000039769.jpg",
            function_to_apply="sigmoid",
        )
        self.assertEqual(
            nested_simplify(outputs, decimals=4),
            [{"label": "LABEL_1", "score": 0.5356}, {"label": "LABEL_0", "score": 0.4612}],
        )
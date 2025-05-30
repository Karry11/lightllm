import json
import os
from lightllm.models.registry import ModelRegistry, llm_model_type_is
from lightllm.common.basemodel.multimodal_tokenizer import BaseMultiModalTokenizer
from lightllm.common.build_utils import repair_config
from lightllm.models.llama.model import LlamaTpPartModel
from lightllm.models.qwen2.model import Qwen2TpPartModel
from lightllm.models.qwen2_vl.model import Qwen2VLTpPartModel
from lightllm.models.qwen2_vl.vision_process import smart_resize
from lightllm.models.qwen_vl.layer_infer.pre_layer_infer import LlamaMultimodalPreLayerInfer
from lightllm.models.tarsier2.layer_weights.pre_and_post_layer_weight import (
    Tarsier2Qwen2PreAndPostLayerWeight,
    Tarsier2LlamaPreAndPostLayerWeight,
)
from lightllm.server.multimodal_params import AudioItem, MultimodalParams, ImageItem
from lightllm.server.core.objs import SamplingParams


class Tarsier2Tokenizer(BaseMultiModalTokenizer):
    def __init__(self, tokenizer=None, image_processor=None, **kwargs):
        super().__init__(tokenizer)
        self.image_processor = image_processor
        self.image_start_id = kwargs["model_cfg"]["text_config"]["vision_start_token_id"]
        self.image_end_id = kwargs["model_cfg"]["text_config"]["vision_end_token_id"]
        self.image_token_id = kwargs["model_cfg"]["text_config"]["image_token_id"]

    def init_imageitem_extral_params(
        self, img: ImageItem, multi_params: MultimodalParams, sampling_params: SamplingParams
    ):
        return

    def init_audioitem_extral_params(
        self, audio: AudioItem, multi_params: MultimodalParams, sampling_params: SamplingParams
    ):
        raise NotImplementedError

    def get_image_token_length(self, img: ImageItem):
        width = img.image_w
        height = img.image_h
        resized_height, resized_width = smart_resize(height=height, width=width)
        self.patch_size = self.image_processor.patch_size
        self.merge_size = self.image_processor.merge_size
        grid_t = 1
        grid_h, grid_w = resized_height // self.patch_size, resized_width // self.patch_size
        merge_length = self.merge_size ** 2
        self.token_num = (grid_t * grid_h * grid_w) // merge_length
        self.image_length = self.token_num
        return self.image_length

    def get_audio_token_length(self, audio: AudioItem):
        raise NotImplementedError

    def encode(self, prompt, multimodal_params: MultimodalParams = None, **kwargs):

        origin_ids = self.tokenizer.encode(prompt)

        # <img><image_pad></img> -> <img></img>
        origin_ids = [token for token in origin_ids if token != self.image_token_id]
        # <img></img> --> <img>id,id+1...id+num</img>
        input_ids = []
        image_id = 0
        start_idx = 0
        while True:
            try:
                start_idx = origin_ids.index(self.image_start_id, start_idx)
                if start_idx + 1 >= len(origin_ids):
                    break
                if origin_ids[start_idx + 1] == self.image_end_id:
                    input_ids.extend(origin_ids[: start_idx + 1])
                    token_id = multimodal_params.images[image_id].token_id
                    token_num = multimodal_params.images[image_id].token_num
                    input_ids.extend(range(token_id, token_id + token_num))
                    input_ids.append(self.image_end_id)
                    origin_ids = origin_ids[start_idx + 2 :]
                    start_idx = 0
                    image_id += 1
                else:
                    raise ValueError("image token error")
            except ValueError:
                break
        input_ids.extend(origin_ids[start_idx:])
        return input_ids


@ModelRegistry("llava", condition=llm_model_type_is("qwen2"))
class Tarsier2Qwen2TpPartModel(Qwen2TpPartModel):
    # weight class
    pre_and_post_weight_class = Tarsier2Qwen2PreAndPostLayerWeight

    # infer class
    pre_layer_infer_class = LlamaMultimodalPreLayerInfer

    def __init__(self, kvargs):
        super().__init__(kvargs)
        return

    def _init_config(self):
        with open(os.path.join(self.weight_dir_, "config.json"), "r") as json_file:
            self.config = json.load(json_file)["text_config"]
        # rename keys
        repair_config(self.config, same_names=["num_attention_heads", "n_head"])
        repair_config(self.config, same_names=["hidden_size", "n_embd", "n_embed"])
        repair_config(self.config, same_names=["num_hidden_layers", "n_layer"])
        return


@ModelRegistry("llava", condition=llm_model_type_is("qwen2_vl"))
class Tarsier2Qwen2VLTpPartModel(Qwen2VLTpPartModel):
    # weight class
    pre_and_post_weight_class = Tarsier2Qwen2PreAndPostLayerWeight

    # infer class
    pre_layer_infer_class = LlamaMultimodalPreLayerInfer

    def __init__(self, kvargs):
        super().__init__(kvargs)
        return

    def _init_config(self):
        with open(os.path.join(self.weight_dir_, "config.json"), "r") as json_file:
            self.config = json.load(json_file)["text_config"]
        # rename keys
        repair_config(self.config, same_names=["num_attention_heads", "n_head"])
        repair_config(self.config, same_names=["hidden_size", "n_embd", "n_embed"])
        repair_config(self.config, same_names=["num_hidden_layers", "n_layer"])
        return


@ModelRegistry("llava", condition=llm_model_type_is("llama"))
class Tarsier2LlamaTpPartModel(LlamaTpPartModel):

    pre_and_post_weight_class = Tarsier2LlamaPreAndPostLayerWeight

    # infer class
    pre_layer_infer_class = LlamaMultimodalPreLayerInfer

    def __init__(self, kvargs):
        super().__init__(kvargs)
        return

    def _init_config(self):
        with open(os.path.join(self.weight_dir_, "config.json"), "r") as json_file:
            self.config = json.load(json_file)["text_config"]
        # rename keys
        repair_config(self.config, same_names=["num_attention_heads", "n_head"])
        repair_config(self.config, same_names=["hidden_size", "n_embd", "n_embed"])
        repair_config(self.config, same_names=["num_hidden_layers", "n_layer"])
        return

import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--port", type=int, default="7860")
parser.add_argument("--model", type=str, default="model/RWKV-5-World-3B-ctx4096.roleplay")
parser.add_argument("--strategy", type=str, default="cuda fp16i8 *20 -> cuda fp16")
parser.add_argument("--listen", action='store_true', help="launch gradio with 0.0.0.0 as server name, allowing to respond to network requests")
parser.add_argument("--cuda_on", type=str, default="0", help="RWKV_CUDA_ON value")
parser.add_argument("--jit_on", type=str, default="1", help="RWKV_JIT_ON value")
parser.add_argument("--share", action="store_true", help="use gradio share")
parser.add_argument("--lang", type=str, default="zh", help="zh: Chinese; en: English")
parser.add_argument("--chat_length", type=int, default=4000, help="max chat length")
parser.add_argument("--autosave", action="store_true", help="auto save state in each turn")
cmd_opts = parser.parse_args()

import os
os.environ["RWKV_JIT_ON"] = cmd_opts.jit_on
os.environ["RWKV_CUDA_ON"] = cmd_opts.cuda_on
current_path = os.path.dirname(os.path.abspath(__file__))
os.environ["PATH"] += f";{current_path}/runtime/Scripts;"

from modules.model_utils import ModelUtils
from modules.ui import UI

if __name__ == "__main__":
  model_util = ModelUtils(cmd_opts)
  model_util.load_model()
  ui = UI(model_util, cmd_opts.lang, cmd_opts.chat_length, cmd_opts.autosave)
  app = ui.create_ui()
  app.queue().launch(
    server_name="0.0.0.0" if cmd_opts.listen else None, 
    share=cmd_opts.share,
    server_port=cmd_opts.port,
    inbrowser=True
  )
import copy
import torch
torch.backends.cudnn.benchmark = True
torch.backends.cudnn.allow_tf32 = True
torch.backends.cuda.matmul.allow_tf32 = True
from rwkv.model import RWKV
from rwkv.utils import PIPELINE
import gc, random

class ModelUtils:

  model = None
  pipline = None
  model_path = None
  strategy = None
  CHUNK_LEN = 100
  END_OF_TEXT = 0
  NEG_INF = -999999999
  AVOID_REPEAT = '.!?,。！？，()（）*'
  AVOID_REPEAT_TOKENS = [11]
  all_state = {}

  def __init__(self, args):
    self.model_path = args.model
    self.strategy = args.strategy

  def load_model(self):
    self.model = RWKV(model=self.model_path, strategy=self.strategy)
    self.pipeline = PIPELINE(self.model, "rwkv_vocab_v20230424")
    for i in self.AVOID_REPEAT:
      dd = self.pipeline.encode(i)
      assert len(dd) == 1
      self.AVOID_REPEAT_TOKENS += dd

  def run_rnn(self, model_tokens, model_state, tokens):
    tokens = [int(x) for x in tokens]
    model_tokens += tokens
    while len(tokens) > 0:
      out, model_state = self.model.forward(tokens[:self.CHUNK_LEN], model_state)
      tokens = tokens[self.CHUNK_LEN:]
    if model_tokens[-1] in self.AVOID_REPEAT_TOKENS:
      out[model_tokens[-1]] = self.NEG_INF
    return out, model_tokens, model_state
  
  def save_all_stat(self, name, last_out, model_tokens, model_state):
    n = f'{name}'
    self.all_state[n] = {
      'out': last_out,
      'rnn': copy.deepcopy(model_state),
      'token': copy.deepcopy(model_tokens)
    }

  def load_all_stat(self, name):
    n = f'{name}'
    model_state = copy.deepcopy(self.all_state[n]['rnn'])
    model_tokens = copy.deepcopy(self.all_state[n]['token'])
    return self.all_state[n]['out'], model_tokens, model_state
  
  def remove_stat(self, name):
    n = f'{name}'
    if n in self.all_state.keys():
      del self.all_state[n]
  
  def get_reply(self, model_tokens, model_state, out, chat_param, ban_token=[]):
    self.clear_cache()
    begin = len(model_tokens)
    out_last = begin
    occurrence = {}
    for i in range(300):
      for n in occurrence:
        if out[n] > 0:
          out[n] = out[n] / (1 + chat_param['presence_penalty'])
        else:
          out[n] = out[n] * (1 + chat_param['presence_penalty'])
      for b in ban_token:
        if b not in self.AVOID_REPEAT_TOKENS:
          out[b] -= chat_param['context_penalty']
      token = self.pipeline.sample_logits(out, chat_param['temperature'], chat_param['top_p'], chat_param['top_k'])
      occurrence[token] = 1
      out, model_tokens, model_state = self.run_rnn(model_tokens, model_state, [token])
      out[self.END_OF_TEXT] = self.NEG_INF
      xxx = self.pipeline.decode(model_tokens[out_last:])
      if '\ufffd' not in xxx: # avoid utf-8 display issues
        out_last = begin + i + 1
      send_msg = self.pipeline.decode(model_tokens[begin:])
      if '\n\n' in send_msg:
        send_msg = send_msg.strip()
        break
    return send_msg, out, model_tokens, model_state
  
  def format_chat_param(self, top_p, top_k, temperature, presence_penalty, context_penalty):
    chat_param = {
      'top_p': top_p,
      'top_k': top_k,
      'temperature': temperature,
      'presence_penalty': presence_penalty,
      'context_penalty': context_penalty
    }
    return chat_param
  
  def clear_cache(self):
    gc.collect()
    torch.cuda.empty_cache()
  
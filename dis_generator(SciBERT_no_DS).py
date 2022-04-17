from tqdm import tqdm
import os
from transformers import BertTokenizer, BertConfig, BertForMaskedLM, pipeline
import numpy as np
import fasttext
import nltk
from nltk.tokenize import word_tokenize
import json

# global variable
# BERT_CLOTH_model
# BERT_DGen_model1
# BERT_CLOTH_DGen_model1
CSG_MODEL_NAME = "SciBERT_CLOTH&DGen_model1"
# bert-base-uncased
# allenai/scibert_scivocab_uncased
PRETRAIN_MODEL_NAME = "allenai/scibert_scivocab_uncased"
TOP_K = 10
STOP_WORDS = ["[MASK]", "[SEP]", "[PAD]", "[CLS]"]


def main():
    # define CSG model path
    model_path = os.path.join("./models/CSG/", CSG_MODEL_NAME)
    print(f"Load CSG model at {model_path}...")

    # load CSG model
    csg_model = BertForMaskedLM.from_pretrained(model_path)
    tokenizer = BertTokenizer.from_pretrained(PRETRAIN_MODEL_NAME)

    # create unmasker
    unmasker = pipeline('fill-mask', tokenizer=tokenizer, model=csg_model, top_k=TOP_K)

    # load DS model
    model_path = r"./models/DS/fasttext_model/wiki_en_ft_model01.bin"
    print(f"Load DS model at {model_path}...")
    ds_model = fasttext.load_model(model_path)

    with open("./datasets/DGen/total_new_cleaned_test.json", "r") as file:
        questions = json.load(file)

    print("Generate distractors...")
    dis_results = list()
    for question in tqdm(questions):
        sent = question["sentence"].replace("**blank**", "[MASK]")
        answer = question["answer"]
        result = generate_dis(unmasker, ds_model, sent, answer)
        # print("result:", result)
        dis_result = {"distractors": question["distractors"], "generations": result}
        dis_results.append(dis_result)

    print("Write to json file...")
    with open(f"./results/result_{CSG_MODEL_NAME}_no_DS.json", "w") as file:
        json.dump(dis_results, file)

    print("Done!")


def generate_dis(unmasker, ds_model, sent, answer):
    target_sent = sent + " [SEP] " + answer
    # print(target_sent)

    result = list()
    for cand in unmasker(target_sent):
        word = cand["token_str"].replace(" ", "")
        if len(word) > 0:  # skip stop words
            result.append(word)
    # print(result)

    # # 0.模型信心分數
    # s0s = [c["s0"] for c in cs]
    # new_s0s = min_max_y(s0s)

    # for i, c in enumerate(cs):
    #     # print(c["word"], new_s0s[i])
    #     c["s0"] = new_s0s[i]
    
    # # 1.單字相似度
    # # print(answer)
    # # print("-"*100)
    # answer_vector = ds_model.get_word_vector(answer)

    # word_similarities = list()
    # for c in cs:
    #     c_vector = ds_model.get_word_vector(c["word"])
    #     word_similarity = similarity(answer_vector, c_vector)
    #     word_similarities.append(word_similarity)

    # new_similarities = min_max_y(word_similarities)

    # for i, c in enumerate(cs):
    #     # print(c["word"], 1-word_similarities[i], 1-new_similarities[i])
    #     c["s2"] = 1-new_similarities[i]

    # # 2.句子相似度
    # #依據訓練過後的BERT所生成選項放入句子做比較
    # correct_sent = sent.replace('[MASK]', answer)
    # # print(correct_sent)
    # # print("-"*100)
    # correct_sent_vector = ds_model.get_sentence_vector(correct_sent)

    # cand_sents = list()
    # for c in cs:
    #     cand_sents.append(sent.replace('[MASK]', c["word"]))

    # sent_similarities = list()
    # #兩句子距離
    # for cand_sent in cand_sents:
    #     cand_sent_vector = ds_model.get_sentence_vector(cand_sent)
    #     sent_similarity = similarity(correct_sent_vector, cand_sent_vector)
    #     sent_similarities.append(sent_similarity)

    # new_similarities = min_max_y(sent_similarities)
    # for i, c in enumerate(cs):
    #     # print(cand_sents[i], 1-sent_similarities[i], 1-new_similarities[i])
    #     c["s2"] = 1-new_similarities[i]

    # # 3.詞性相似度
    # origin_token = word_tokenize(sent)
    # origin_token.remove("[")
    # origin_token.remove("]")
    # # print(origin_token)

    # mask_index = origin_token.index("MASK")
    # # print(mask_index)

    # correct_token = word_tokenize(correct_sent)
    # # print(correct_token)
    # correct_pos = nltk.pos_tag(correct_token)
    # # print(correct_pos)

    # answer_pos = correct_pos[mask_index]
    # # print(answer_pos)
    # # print("-"*100)

    # for i, c in enumerate(cs):
    #     cand_sent_token = word_tokenize(cand_sents[i])
    #     cand_sent_pos = nltk.pos_tag(cand_sent_token)
    #     cand_pos = cand_sent_pos[mask_index]

    #     if cand_pos[1] == answer_pos[1]:
    #         c["s3"] = 1.0
    #     else:
    #         c["s3"] = 0.0
        
    #     # print(cand_pos, c["s3"])

    # # 加上權重 (final score)
    # cs_rank = list()
    # for c in cs:
    #     fs = 0.25*c["s0"] + 0.25*c["s1"] + 0.25*c["s2"] + 0.25*c["s3"]
    #     cs_rank.append((c["word"], fs))

    # cs_rank.sort(key = lambda x: x[1], reverse=True)
    # # print("cs_rank:", cs_rank)

    # # Top 3
    # result = [d[0] for d in cs_rank[:10]]

    return result


# cosine similarity
def similarity(v1, v2):
    n1 = np.linalg.norm(v1)
    n2 = np.linalg.norm(v2)
    if n1 == 0 or n2 == 0:
        return 1
    else:
        return np.dot(v1, v2) / (n1 * n2)


# Min-Max 歸一化
def min_max_y(raw_data):
  # 裝進標準化後的新串列
  min_max_data = []
  
  # 進行Min-Max標準化
  for d in raw_data:
    min_max_data.append((d - min(raw_data)) / (max(raw_data) - min(raw_data)))
             
  # 回傳結果
  return min_max_data


if __name__ == "__main__":
    main()

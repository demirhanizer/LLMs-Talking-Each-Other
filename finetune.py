import os
import torch
import gc
from transformers import AutoTokenizer, AutoModelForCausalLM, Trainer, TrainingArguments, BitsAndBytesConfig
from datasets import load_dataset
from peft import get_peft_model, LoraConfig, TaskType
from peft import PeftModel

os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
torch.backends.cudnn.benchmark = True  

model_name = "meta-llama/Llama-3.1-8B"
model = AutoModelForCausalLM.from_pretrained(model_name, device_map="auto")

adapter_path = "suayptalha/Llama-3.1-8b-Turkish-Finetuned"
model = PeftModel.from_pretrained(model, adapter_path)

tokenizer = AutoTokenizer.from_pretrained(model_name)
tokenizer.pad_token = tokenizer.eos_token

quant_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16
)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    quantization_config=quant_config,
    device_map="auto",
    torch_dtype=torch.float16,
    use_cache=False
)

lora_config = LoraConfig(
    task_type=TaskType.CAUSAL_LM,
    r=1,
    lora_alpha=4,
    target_modules=["q_proj", "v_proj"],
    lora_dropout=0.1
)
model = get_peft_model(model, lora_config)

train_dataset = load_dataset(
    'json',
    data_files='/cta/users/elalem2/converted_file.jsonl',
    split='train'
)

training_args = TrainingArguments(
    output_dir="./results",
    per_device_train_batch_size=2,
    gradient_accumulation_steps=2,
    num_train_epochs=3,
    fp16=True,
    logging_dir='./logs',
    logging_steps=500,
    save_steps=1000,
    optim="adamw_torch",  
    evaluation_strategy="no",
    lr_scheduler_type="cosine", 
    max_grad_norm=1.0,
    learning_rate=0.0001,
    warmup_steps=500,
    save_total_limit=2,
)

def preprocess_function(examples):
    outputs = [q + " " + a for q, a in zip(examples["Question"], examples["Answer"])]
    model_inputs = tokenizer(outputs, padding="max_length", truncation=True, max_length=500)
    labels = model_inputs["input_ids"]
    model_inputs["labels"] = [
        [(label if label != tokenizer.pad_token_id else -100) for label in example]
        for example in labels
    ]
    return model_inputs

train_dataset = train_dataset.map(preprocess_function, batched=True, remove_columns=["Question", "Answer"], num_proc=2)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
)

torch.cuda.empty_cache()
gc.collect()

trainer.train()

trainer.save_model("./results/optimized_fp16_lora_model")
torch.cuda.empty_cache()
gc.collect()

from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
from transformers import BitsAndBytesConfig
import torch
import time
from flask import Flask, request, jsonify
import os
import traceback
import re

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "Flask API is running!"

# Environment variable for better memory management
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

# Model and adapter paths
model_id = "google/gemma-2-9b-it"
adapter_path = "/home/elalem/claim_questions/{}"

def load_model_and_tokenizer():
    print(f"Loading tokenizer from: {model_id}")
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    print("Loading model...")
    device = torch.device("cuda")
    quant_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True
    )

    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        quantization_config=quant_config,
        device_map="auto",
        torch_dtype=torch.float16,
        use_cache=True
    )

    model.gradient_checkpointing_enable()
    return model, tokenizer, device

model, tokenizer, device = load_model_and_tokenizer()

def load_adapter_for_model(adapter_name):
    try:
        return PeftModel.from_pretrained(model, adapter_path.format(adapter_name), adapter_name=adapter_name)
    except Exception as e:
        raise ValueError(f"Adapter '{adapter_name}' could not be loaded. Ensure it exists. Error: {str(e)}")

@app.route("/generate_llm_to_llm", methods=["POST"])
def generate_llm_to_llm():
    data = request.get_json()

    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON format"}), 400

    # Extracting input fields
    prompt_1 = data.get("prompt_1", "").strip()  # First message (initial prompt)
    persona_1 = data.get("persona_name", "").strip()  # First persona name
    persona_2 = data.get("prompt_2", "").strip()  # Second persona name (this is actually the second persona)
    iterations = data.get("iterations", 3)

    # Validate input
    if not prompt_1:
        return jsonify({"error": "The first prompt is required"}), 400
    if not persona_1 or not persona_2:
        return jsonify({"error": "Both persona names are required"}), 400
    if not isinstance(iterations, int) or iterations <= 0:
        return jsonify({"error": "Iterations must be a positive integer"}), 400

    try:
        conversation = []
        last_response_llm1 = prompt_1  # Initial message from the user
        last_response_llm2 = ""  # Initially, LLM2 has no response

        # Load adapters for personas
        app.logger.info(f"Loading adapter for persona_1: {persona_1}")
        adapter_path_persona_1 = adapter_path.format(persona_1)
        model_1 = PeftModel.from_pretrained(model, adapter_path_persona_1, adapter_name=persona_1)

        app.logger.info(f"Loading adapter for persona_2: {persona_2}")
        adapter_path_persona_2 = adapter_path.format(persona_2)
        model_2 = PeftModel.from_pretrained(model, adapter_path_persona_2, adapter_name=persona_2)

        # Iteratively generate responses
        for i in range(iterations):
            # Generate response from LLM1
            llm1_input = f"LLM2: {last_response_llm2}\nBu yazar (LLM2) bahsedilen konuda böyle bir şey dedi. Senin bu konu hakkındaki düşüncelerin nedir? Karşı yazarın verdiği cevaba göre onun yanıtını göz önünde bulundurarak yeni bir cevap üret."
            inputs = tokenizer(
                llm1_input,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=128,
                return_attention_mask=True
            )
            inputs = {k: v.to(device) for k, v in inputs.items()}
            outputs = model_1.generate(
                **inputs,
                max_new_tokens=50,
                temperature=0.7,
                top_p=0.9,
                do_sample=True
            )
            response_1 = tokenizer.decode(outputs[0], skip_special_tokens=True).strip()

            if not response_1:
                raise ValueError("LLM1 generated an empty response.")

            conversation.append({"llm_1_response": response_1})
            last_response_llm1 = response_1

            # Generate response from LLM2
            llm2_input = f"LLM1: {response_1}\nBu yazar (LLM1) bahsedilen konuda böyle bir şey dedi. Senin bu konu hakkındaki düşüncelerin nedir? Karşı yazarın verdiği cevaba göre onun yanıtını göz önünde bulundurarak yeni bir cevap üret."
            inputs = tokenizer(
                llm2_input,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=128,
                return_attention_mask=True
            )
            inputs = {k: v.to(device) for k, v in inputs.items()}
            outputs = model_2.generate(
                **inputs,
                max_new_tokens=50,
                temperature=0.7,
                top_p=0.9,
                do_sample=True
            )
            response_2 = tokenizer.decode(outputs[0], skip_special_tokens=True).strip()

            if not response_2:
                raise ValueError("LLM2 generated an empty response.")

            conversation.append({"llm_2_response": response_2})
            last_response_llm2 = response_2

        # Return the conversation as a response
        return jsonify({"conversation": conversation})

    except ValueError as ve:
        app.logger.error(f"Validation error during LLM-to-LLM interaction: {str(ve)}")
        return jsonify({"error": f"Validation Error: {str(ve)}"}), 400

    except Exception as e:
        app.logger.error(f"Unexpected error during LLM-to-LLM interaction: {traceback.format_exc()}")
        return jsonify({"error": f"Internal Server Error: {str(e)}"}), 500


@app.route("/generate_multi_llm", methods=["POST"])
def generate_multi_llm():
    try:
        # Parse and validate incoming JSON data
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data received"}), 400

        selected_personas = data.get("selected_personas", [])
        claim = data.get("claim", "").strip()
        iterations = data.get("iterations", 5)

        if not selected_personas:
            return jsonify({"error": "selected_personas is empty"}), 400
        if not claim:
            return jsonify({"error": "claim is empty"}), 400
        if not isinstance(iterations, int) or iterations <= 0:
            return jsonify({"error": "Invalid iterations value"}), 400

        # Ensure personas are unique and valid
        selected_personas = [p.strip().lower() for p in selected_personas if p.strip()]
        if len(set(selected_personas)) != len(selected_personas):
            return jsonify({"error": "Duplicate personas found in selected_personas"}), 400

        torch.cuda.empty_cache()

        app.logger.info("START INFERENCE")
        start_time = time.time()

        # Load the initial LoRA adapter
        peft_model = PeftModel.from_pretrained(
            model, adapter_path.format(selected_personas[0]), adapter_name=selected_personas[0]
        )
        adapters = {}
        adapter_names = []

        # Load all adapters for the selected personas
        for persona_name in selected_personas:
            adapter_path_persona = adapter_path.format(persona_name)
            app.logger.info(f"Loading adapter for persona: {persona_name}")
            adapters[persona_name] = peft_model.load_adapter(adapter_path_persona, persona_name)
            adapter_names.append(persona_name)

        # Prepare the initial input
        system_message = "Sen bir Türk köşe yazarısın. Görevin sorulan soru hakkındaki fikrini ve gerekçesini açıklamaktır."

        conversation = []
        input_prompts = []

        for persona_name in selected_personas:
            question = claim
            input_prompts.append(
                [{"role": "user", "content": f"{system_message}\n\n{question}"}]
            )

        # Validate input_prompts structure
        if not all(isinstance(p, list) and "role" in p[0] and "content" in p[0] for p in input_prompts):
            return jsonify({"error": "Invalid input_prompts format"}), 500

        # Tokenize all prompts in parallel
        input_ids = tokenizer.apply_chat_template(
            input_prompts,
            return_tensors="pt",
            return_dict=True,
            add_generation_prompt=True,
        ).to("cuda")

        # Validate the consistency between adapter_names and input_prompts
        if len(adapter_names) != len(input_prompts):
            return jsonify({"error": "Mismatch between adapter_names and input_prompts"}), 500

        # Generate responses in parallel
        outputs = peft_model.generate(
            **input_ids, adapter_names=list(adapters.keys()), max_new_tokens=256
        )

        # Decode all outputs
        for i, output in enumerate(outputs):
            response = tokenizer.decode(output, skip_special_tokens=True).strip()
            response = response.split("\nmodel\n")[1].strip()
            response = re.sub(r"</?div.*?>", "", response).strip()



            conversation.append({"persona": adapter_names[i], "response": response})

        end_time = time.time()
        app.logger.info("END INFERENCE")
        app.logger.info(f"Total time taken: {end_time - start_time:.2f} seconds")

        return jsonify({"conversation": conversation}), 200
   
    except Exception as e:
        app.logger.error(f"Error in generate_multi_llm: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500



    

@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()
    app.logger.info(f"Received payload: {data}")

    # Validate input data
    prompt = data.get("prompt", "").strip()
    persona_name = data.get("persona_name", "").strip()
    if not prompt:
        return jsonify({"error": "No prompt provided"}), 400
    if not persona_name:
        return jsonify({"error": "No persona name provided"}), 400

    try:
       

        # Tokenize the input
        # Load the adapter using persona_name
        adapter_path_persona = adapter_path.format(persona_name)
        peft_model = PeftModel.from_pretrained(model, adapter_path_persona, adapter_name=persona_name)
        app.logger.info(f"Using adapter: {persona_name}")

        system_message = "Sen bir Türk köşe yazarısın. Görevin sorulan soru hakkındaki fikrini ve gerekçesini açıklamaktır."
        question = prompt

        input_prompt = [
            {"role": "user", "content": f"{system_message}\n\n{prompt}"},
        ]
        input_ids = tokenizer.apply_chat_template(input_prompt, return_tensors="pt", return_dict=True).to("cuda")

        # Generate response
        outputs = peft_model.generate(
            **input_ids,
            max_new_tokens=256,
        )

        # Decode generated text
        generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        generated_text = generated_text.split("\nmodel\n")[1].strip()
        app.logger.info(f"Generated text: {generated_text}")

        return jsonify({"response": generated_text})

    except torch.cuda.OutOfMemoryError:
        app.logger.error(f"Out of memory for persona: {persona_name}. Skipping...")
        torch.cuda.empty_cache()
        return jsonify({"error": "Out of memory, try again later."}), 500
    except ValueError as e:
        app.logger.error(f"Error with persona {persona_name}: {e}")
        return jsonify({"error": f"Invalid persona: {persona_name}. {str(e)}"}), 400
    except Exception as e:
        app.logger.error(f"Error during generation: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


    


if __name__ == "__main__":
    app.run(host="10.3.0.96", port=5000, debug=False)

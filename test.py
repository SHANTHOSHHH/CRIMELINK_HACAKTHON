from llama_cpp import Llama

model_path = "D:\\mistral\\models\\mistral-7b-instruct-v0.2.Q3_K_M.gguf"  # Ensure this is correct
llm = Llama(model_path=model_path)  # Try removing extra parameters

response = llm("Hello, how are you?")
print(response)

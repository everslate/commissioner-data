from openai import OpenAI

client = OpenAI(
  api_key="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"
)

response = client.responses.create(
  model="gpt-5-nano",
  input="write a haiku about ai",
  store=True,
)

print(response.output_text);

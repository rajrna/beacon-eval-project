# import os, boto3
# os.environ['AWS_BEARER_TOKEN_BEDROCK'] = 'your-key'
# client = boto3.client('bedrock-runtime', region_name='us-east-1')
# for model in [
#     'us.anthropic.claude-3-5-haiku-20241022-v1:0',
#     'us.anthropic.claude-sonnet-4-5-20251001-v1:0',
#     'global.anthropic.claude-haiku-4-5-20251001-v1:0',
#     'us.anthropic.claude-3-haiku-20240307-v1:0',
# ]:
#     try:
#         r = client.converse(
#             modelId=model,
#             messages=[{'role': 'user', 'content': [{'text': 'hi'}]}]
#         )
#         print(f'WORKS: {model}')
#     except Exception as e:
#         print(f'FAIL: {model} -> {str(e)[:80]}')


import os, boto3
os.environ['AWS_BEARER_TOKEN_BEDROCK'] = 'your-full-key-here'
client = boto3.client('bedrock-runtime', region_name='us-east-1')
print('client created:', client)
print('bearer token set:', bool(os.environ.get('AWS_BEARER_TOKEN_BEDROCK')))

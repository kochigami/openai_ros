#!/usr/bin/env python3

from openai_ros.msg import StringArray
from openai_ros.srv import Completion, CompletionResponse
from naoqi_bridge_msgs.srv import SetString, SetStringResponse
from naoqi_bridge_msgs.srv import GetString, GetStringResponse
import rospy
from openai import OpenAI

# Global variable to store system content
system_message = ""

def set_system_content(req):
    global system_message
    system_message = req.data
    rospy.loginfo("System message updated: %s", system_message)
    res = SetStringResponse()
    res.success = True
    return res

def get_system_content(req):
    global system_message
    rospy.loginfo("System message obtained: %s", system_message)
    res = GetStringResponse()
    res.data = system_message
    return res

def legacy_servicer(req):
    global client, max_tokens, model
    res = CompletionResponse()

    response = client.completions.create(model=model, prompt=req.prompt, temperature=req.temperature, max_tokens=max_tokens)

    res.finish_reason = response.choices[0].finish_reason
    res.text = response.choices[0].text
    res.model = response.model
    res.completion_tokens = response.usage.completion_tokens
    res.prompt_tokens = response.usage.prompt_tokens
    res.total_tokens = response.usage.total_tokens

    # When response is not working, completion_tokens is None, which chase error on CompleteResponse format(int32)
    if not isinstance(res.completion_tokens, int):
        res.completion_tokens = -1
    return res

def chat_servicer(req):
    global client, max_tokens, model, message_history, max_history_length

    res = CompletionResponse()

    if system_message:  # Check if there is a system message to include
        message_history.append({"role": "system", "content": system_message})

    message_history.append({"role": "user", "content": req.prompt})
    response = client.chat.completions.create(model=model, messages=message_history, temperature=req.temperature, max_tokens=max_tokens)

    message_history.append({"role": "assistant", "content": response.choices[0].message.content})
    while len(message_history) > max_history_length:
        message_history.pop(0)

    rospy.loginfo(response)

    res.finish_reason = response.choices[0].finish_reason
    res.text = response.choices[0].message.content
    res.model = response.model
    res.completion_tokens = response.usage.completion_tokens
    res.prompt_tokens = response.usage.prompt_tokens
    res.total_tokens = response.usage.total_tokens

    # When response is not working, completion_tokens is None, which chase error on CompleteResponse format(int32)
    if not isinstance(res.completion_tokens, int):
        res.completion_tokens = -1
    return res

def main():
    global client, max_tokens, model, message_history, max_history_length
    pub = rospy.Publisher('available_models', StringArray, queue_size=1, latch=True)
    rospy.init_node('openai_node', anonymous=True)

    rospy.Service('set_system_content', SetString, set_system_content)
    rospy.Service('get_system_content', GetString, get_system_content)

    client = OpenAI(api_key=rospy.get_param('~key'), base_url=rospy.get_param('~base_url'))
    max_tokens = rospy.get_param('~max_tokens', default=256)
    max_history_length = rospy.get_param('~max_history_length', default=12)
    model = rospy.get_param('~model', default='gpt-3.5-turbo')

    message_history = []

    models_msg = StringArray()
    for m in client.models.list():
        models_msg.data.append(m.id)

    if model not in models_msg.data:
        rospy.logerr(model + " is not an available model")
        rospy.logerr(models_msg.data)
        return

    pub.publish(models_msg)

    endpoint = "chat"
    try:
        client.chat.completions.create(model=model, messages=[{"role": "user", "content": "ignore this message"}], max_tokens=1)
    except:
        endpoint = "legacy"

    rospy.loginfo("Using " + model + " though " + endpoint + " endpoint")

    if endpoint == "legacy":
        rospy.Service('get_response', Completion, legacy_servicer)
    else:
        rospy.Service('get_response', Completion, chat_servicer)

    rospy.spin()

if __name__ == '__main__':
    try:
        main()
    except rospy.ROSInterruptException:
        pass

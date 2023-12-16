#!/usr/bin/env python
import rospy
from openai_ros.srv import GptService, GptServiceResponse
from naoqi_bridge_msgs.srv import SetString, SetStringResponse
from naoqi_bridge_msgs.srv import GetString, GetStringResponse
import openai

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
 
def chat_with_gpt(req):
    openai.api_key = rospy.get_param('~key')

    try:
        messages = []
        if system_message:  # Check if there is a system message to include
            messages.append({"role": "system", "content": system_message})

        # Add the user message
        messages.append({"role": "user", "content": req.prompt})
        rospy.loginfo("User: %s", req.prompt)

        # Call the chat model here    
        response = openai.ChatCompletion.create(
            model = rospy.get_param('~model', default='gpt-3.5-turbo'),
            messages=messages
            # messages=[
            #     {"role": "system", "content": "You are a helpful assistant."},
            #     {"role": "user", "content": req.prompt}
            # ]
        )

        # Extract the assistant's (AI's) text from the response
        res = response['choices'][0]['message']['content']
        rospy.loginfo("Assistant: %s", res)
        messages.append({"role": "assistant", "content": res})

        tokens = response["usage"]["total_tokens"]
        print("Num of tokens: " + str(tokens))

        return GptServiceResponse(res)
    except Exception as e:
        rospy.logerr("Failed to call OpenAI API: %s", e)
        return GptServiceResponse("Error: Could not process your request.")
  
def gpt_service():
    rospy.init_node('gpt_service')
    rospy.Service('set_system_content', SetString, set_system_content)
    rospy.Service('get_system_content', GetString, get_system_content)
    rospy.Service('chat_with_gpt', GptService, chat_with_gpt)
    print("Ready to handle GPT-3.5 requests.")
    rospy.spin()
 
if __name__ == "__main__":
    gpt_service()

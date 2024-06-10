import streamlit as st

st.set_page_config(
    page_title="Hello",
    page_icon="👋",
    initial_sidebar_state="expanded",
    layout="wide",
)

st.write("# Welcome to Motion's SIGMOD Demo! 👋")

st.sidebar.success("Select a mode of exploration.")

st.markdown(
    """
    Motion is a framework that enables LLM pipeline developers to define and incrementally maintain self-updating prompts in Python.
    
    **👈 Select a mode of exploration** to either (as an end-user) interact with a Motion-powered application or (as a developer) explore summaries of user feedback and external context incrementally maintained by Motion.
    
    ### Be an End-User: Explore our AI Stylist Application
    - Our AI stylist application takes into consideration some basic information about you and suggests items to buy for events of your choice.
    - You can toggle between using Motion's summaries and not using them to see the difference in the quality of recommendations and the speed of the application. 
    - Using Motion uses summaries of your feedback and external context in prompts to suggest items to buy for your specific event.
    - Not using Motion simply uses *all* content retrieved by RAG (previous recommendations to avoid, your feedback/what you like or dislike, Fashion trends from Google News, etc.) in the prompt.
    ### Be a Developer: Explore Summaries Used as Prompt Sub-Parts and Real-Time Prompt Updates
    - Explore the summaries incrementally maintained by Motion. There is a global summary of fashion trends (used for all users' prompts) and user-specific summaries of feedback and their query history.
    - You can select a user to inspect their summaries.
    - You can see the news articles that are used to generate the global summary (it is updated every 10 minutes).
    - You can see a timeline of user interactions (that will be used to update the user-specific summaries).
    ### Want to learn more about Motion?
    - Visit [Motion's github repo](https://github.com/dm4ml/motion)
    - Dive into our [documentation](https://dm4ml.github.io/motion/docs)
    - Check out the [Source Code](https://github.com/shreyashankar/motion-sigmod-demo)
    - Read our [Demo Paper](https://www.sh-reya.com/motion_sigmod_demo.pdf)
"""
)

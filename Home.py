import streamlit as st

st.set_page_config(
    page_title="Hello",
    page_icon="👋",
    layout="wide",
)

st.write("# Welcome to Motion's SIGMOD Demo! 👋")

st.sidebar.success("Select a mode of exploration.")

st.markdown(
    """
    Motion is a framework that enables LLM pipeline developers to define and incrementally maintain self-updating prompts in Python.
    
    **👈 Select a mode of exploration** to either (as an end-user) interact with a Motion-powered application or (as a developer) explore summaries of user feedback and external context incrementally maintained by Motion.
    
    ### Be an End-User: Explore our AI Stylist Application
    - Our stylist application uses your basic information to recommend items for your chosen events.
    - Toggle Motion's summaries on or off to compare recommendation quality and application speed.
    - With Motion, summaries of your feedback and external context enhance item suggestions for your events.
    - Without Motion, the application uses all available content, including past recommendations, your preferences, and current fashion trends.
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

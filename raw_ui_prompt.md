## Final Refined Text

Help me write a prompt for Jules (Google vibe-coding platform) to design a modern UI for my application using Next.js, Tailwind CSS, if necessary Shadcn/ui, or similar modern technologies.

I have an existing Python program. This program takes a codebase and **generates** a tutorial for it in Markdown format using AI agents and LLMs.

Now we require a UI for this application.

In the UI, we envision the following scenario:

Let's say we have five codebases that have been turned into tutorials. When the UI opens, we should display several interactive cards, similar to this project: [https://cot-visualizer.online/](https://cot-visualizer.online/).

Each card represents a codebase. These cards must be interactive, modern, and include animations.

When the user clicks on a card, a temporary loading page should appear, featuring an interactive, modern, and visually appealing progress bar. Since the multi-agent system processing large codebases normally takes several hours, we require the progress bar to complete the transition in only three or four seconds for the demo. This duration must be adjustable via **environment variables**. Upon completion, the tutorial page will be unveiled. Our tutorials are in Markdown format; paths specified in the environment variables will be used to gather the relevant Markdown files for that codebase and render them. Since these Markdown files contain Mermaid.js diagrams, our Markdown renderer must easily render them. The user should also be able to easily zoom in, zoom out, or scroll the displayed Markdown files.

Furthermore, while the user is viewing the Markdown files, a panel on the left-hand side should display the available Markdown files for that repository, allowing the user to select them (similar to a chat history panel where users select chats, but displaying the Markdown files for the current repository instead).

Crucially, the user must be able to toggle between a preview mode and a Markdown edit mode. Essentially, we are implementing a basic Markdown editor with a preview function. When the user first opens a tutorial, the files are in preview mode, but the user should be able to toggle to edit mode and modify the Markdown content.

The UI should be complete, including a distinct header and footer, effective back buttons, and UI elements with smooth animations and transitions. We seek a highly advanced, modern, **AI-themed user interface.**

For example, the UI in this image is appealing: [Image reference is missing, but the text is kept as is.]

The project title is **"Codebase Tutorial Generator."**

The footer must include the names of the developers, their GitHub links, and appropriate icons.

The deliverable should be a fully functional, **end-to-end working project.**

Finally, after the UI is developed, we require a `GUIDE.md` file detailing how to build and run the project, how to modify environment variables, etc.

We must also update the existing README file. The update should integrate the new project information without losing the content of the previous README.

PLEASE NOTE THAT a Python project already exists here. We require a monorepo structure containing both Python and TypeScript programs. Care must be taken to ensure that these two parts do not conflict with or break one another. Below is the file structure of the existing Python project to better aid in designing the prompt:

[File structure details are missing, but the text is kept as is.]

Our Markdown tutorials are static and pre-generated. Therefore, the UI should only need to read their metadata from a `content.yaml` configuration file. This configuration file will enable the UI to display the correct cards upon build and load the appropriate Markdown files into the left panel for each codebase tutorial.

For example, developers should be able to specify the names of the codebases and their respective Markdown file paths within `content.yaml`.
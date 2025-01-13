# PyBCM - Python Business Capability Modeler

> **NOTICE:** The `pybcm-noai` branch does not include built-in LLM generation or chat features, and AI-powered capability generation is supported exclusively through smart copy/paste features, allowing integration with browser-based AI chat agents like ChatGPT. If you do not have access to common API powered LLM services supported by PydanticAI, then choose the `pybcm-noai` branch. 

**PyBCM** is a powerful and user-friendly Business Capability Modeling (BCM) application built with Python. It provides an intuitive graphical interface for creating, visualizing, and managing hierarchical business capability models. This tool is designed to help business architects, analysts, and strategists map and understand their organization's capabilities effectively.

![PyBCM Screenshot](https://github.com/ThomasRohde/PyBCM/blob/master/images/image.png?raw=true)

## Key Features

PyBCM offers a comprehensive set of features to support various aspects of business capability modeling:

### Core Capability Management

*   **Hierarchical Tree View:**  Visualize and navigate your capability model in an intuitive tree structure.
*   **Drag-and-Drop Reordering:** Easily rearrange capabilities within the hierarchy by simply dragging and dropping them.
*   **CRUD Operations:** Create, read, update, and delete capabilities seamlessly.
*   **Rich Text Descriptions:**  Add detailed descriptions to capabilities using Markdown, with real-time preview and automatic saving.
*   **Persistent Storage:** Utilizes a robust SQLite database to store your capability model reliably.
*   **Search Functionality:** Quickly find capabilities by name or description using the built-in search bar.
*   **Import/Export:** Import and export your entire capability model in JSON format for easy sharing and backup.

### Advanced AI Assistance

*   **AI-Powered Expansion:**  Leverage the power of large language models (LLMs) to automatically generate sub-capabilities based on selected capabilities.
*   **First-Level Capability Generation:** Use AI to create initial high-level capabilities from an organization name and description.
*   **Customizable AI Settings:** Configure the maximum number of AI-generated capabilities and adjust settings for initial capability creation.
*   **AI Chat Interface:** Interact with an AI assistant to explore your capability model, search capabilities, and get insights.

### Interactive Visualization

*   **Dynamic Visualizer:** Generate interactive visualizations of your capability model within a dedicated window.
*   **Zoom and Pan:**  Easily navigate the visualization using zoom (Ctrl + Mouse Wheel) and pan (click and drag).
*   **Color-Coded Levels:** Visually distinguish different levels of the capability hierarchy with customizable color schemes.
*   **Tooltips:** Hover over capabilities to view their detailed descriptions.
*   **Auto-Layout:**  Intelligent layout algorithms automatically arrange capabilities for optimal clarity and readability.
    *   **Standard Layout:** A balanced layout algorithm suitable for most models.
    *   **High-Quality (HQ) Layout:** An advanced algorithm that optimizes for aspect ratio and space utilization, especially useful for complex models.
*   **Customizable Visualization Settings:** Adjust layout parameters, colors, font sizes, and more to tailor the visualization to your preferences.

### Export Options

*   **SVG Export:** Generate high-quality vector graphics (SVG) of your capability model for use in documentation, presentations, and web pages.
*   **PowerPoint Export:** Export your capability model directly to a PowerPoint presentation, preserving layout and styling for seamless integration into your reports.
*   **Archimate Open Exchange Format:** Export your capability model in Archimate Open Exchange format, making it compatible with popular enterprise architecture tools like Archi.
*   **Audit Log Export:** Export detailed audit logs of all changes made to your capability model in Excel format.

### Audit Logging and Security

*   **Detailed Audit Trail:** Track all changes to your capability model, including creation, updates, deletions, and moves, with timestamps and details of old and new values.
*   **Audit Log Viewer:** A dedicated interface to view, search, and filter audit logs.
*   **Excel Export:** Export audit logs to an Excel file for further analysis and reporting.
*   **Secure Database:** The application uses SQLite with foreign key constraints enabled by default to ensure data integrity and prevent unauthorized modifications.

## Installation

### Prerequisites

*   Python 3.11 or higher
*   `uv` package manager (recommended for faster dependency management)

### Steps

1. **Clone the repository:**

    ```bash
    git clone https://github.com/yourusername/pybcm.git
    cd pybcm
    ```

2. **Install dependencies using `uv`:**

    ```bash
    uv pip install -e .
    ```

3. **Alternative: Run as a uv tool:**

    You can install bcm directly as a uv tool:

    ```bash
    uv tool install pybcm
    bcm
    ```

4. **Updating the Project:**

    To update PyBCM to the latest version from GitHub:

    1. Navigate to your local repository:
       ```bash
       cd path/to/pybcm
       ```
    
    2. Pull the latest changes:
       ```bash
       git pull origin master
       ```
    
    3. Update dependencies:
       ```bash
       uv pip install -e .
       ```
    
    Note: Before updating, it's recommended to:
    - Back up your `.pybcm` directory in case you've made custom template modifications
    - Check the release notes on GitHub for any breaking changes
    - Export your capability models if you want to be extra cautious

5. **Configure LLM API Keys:**

    PyBCM uses PydanticAI to interact with various LLM providers. You'll need to:

    1. Copy the sample environment file to your user directory:
       ```bash
       mkdir -p ~/.pybcm
       cp .env.sample ~/.pybcm/.env
       ```
    2. Edit `~/.pybcm/.env` and configure your environment:

       Required variables:
       - `OPENAI_API_KEY`: Your OpenAI API key (required for default setup)

       Optional LLM providers:
       - `ANTHROPIC_API_KEY`: For Claude models
       - `GOOGLE_API_KEY`: For Gemini models
       - `GROQ_API_KEY`: For Groq models
       - `MISTRAL_API_KEY`: For Mistral models

       Model settings:
       - `DEFAULT_MODEL`: Model to use (default: gpt-4-turbo-preview)
       - `MAX_TOKENS`: Maximum response length (default: 2000)
       - `TEMPERATURE`: Response creativity 0.0-1.0 (default: 0.7)

       See the [Logfire documentation](https://logfire.pydantic.dev/docs/reference/configuration/#using-environment-variables) for setting environment variables for logging.
    
    The application validates these settings on startup and will show an error if required variables are missing.

6. **Configure Logfire logging (first time only):**

    PyBCM uses Logfire for advanced logging and monitoring. On first run, you'll need to:

    1. Create a Logfire account at [logfire.pydantic.dev](https://logfire.pydantic.dev)
    2. Install the Logfire CLI:
       ```bash
       uv pip install logfire
       ```
    3. Authenticate with Logfire:
       ```bash
       logfire auth
       ```
    4. Create and select a project:
       ```bash
       logfire projects new pybcm
       logfire projects use pybcm
       ```

    This only needs to be done once. Credentials are stored in `~/.logfire/default.toml`.


## Usage

### Launching the Application

Run the application from the command line:

```bash
bcm
```

### Basic Navigation

*   **Tree View:** The left panel displays the hierarchical capability tree.
*   **Description:** The right panel shows the description of the selected capability.
*   **Toolbar:** Provides quick access to common actions like expand/collapse, AI expansion, visualization, search, and editing.
*   **Menu Bar:** Offers more advanced options, including import/export, settings, and audit log management.

### Managing Capabilities

1. **Adding a Capability:**
    *   Right-click on the desired parent in the tree view and select "New Child."
    *   Enter the capability name and an optional description.
    *   Click "OK."

2. **Updating a Capability:**
    *   Select a capability in the tree view.
    *   Click "Edit" in the toolbar to switch to edit mode.
    *   Modify the name or description in the right panel.
    *   Click "View" to see a markdown preview or "Save" to save changes to the database.

3. **Deleting a Capability:**
    *   Right-click on the capability in the tree view and select "Delete."
    *   Confirm the deletion.

4. **Reordering Capabilities:**
    *   Drag and drop capabilities within the tree view to change their order or parent.

5. **Copy/Paste Capabilities:**
    *   **Copy (Ctrl+C):** Select a capability and press Ctrl+C to copy its context to the clipboard in a format suitable for AI expansion.
    *   **Paste (Ctrl+V):** Select a parent capability, then press Ctrl+V to paste a JSON array of sub-capabilities. Each capability in the array must have `name` and `description` fields.
    *   This allows you to:
        - Copy capability context for use with external AI tools
        - Paste pre-defined sets of capabilities from JSON
        - Share capability structures between models

### Using AI Features

1. **AI Capability Expansion:**
    *   Select a capability in the tree view.
    *   Click the "✨" (sparkles) button in the toolbar.
    *   Review the AI-generated sub-capabilities.
    *   Check the boxes next to the capabilities you want to add.
    *   Click "OK."

2. **AI Chat:**
    *   Click the "🤖" (robot) button in the toolbar.
    *   A new browser window will open, allowing you to interact with the AI assistant.
    *   Ask questions about your capability model, search for capabilities, and get insights using natural language.

### Working with Visualizations

1. **Opening the Visualizer:**
    *   Click the "🗺️" (map) button in the toolbar or select "Visualize Model" from the "Edit" menu.
    *   A new window opens displaying the interactive visualization.

2. **Navigation:**
    *   **Zoom:** Use Ctrl + Mouse Wheel to zoom in and out.
    *   **Pan:** Click and drag to move around the canvas.

3. **Tooltips:**
    *   Hover your mouse over a capability to view its description in a tooltip.

4. **Exporting:**
    *   **SVG:** Select "File" > "Export to SVG..." to save the visualization as an SVG file.
    *   **PowerPoint:** Select "File" > "Export to PowerPoint..." to generate a PowerPoint presentation.
    *   **Archimate:** Select "File" > "Export to Archimate..." to create an Archimate Open Exchange file.

5. **Customization:**
    *   Access visualization settings through "File" > "Settings."
    *   Customize colors, layout parameters, font sizes, and more.

### Settings

Access the application settings through "File" > "Settings." Here you can customize:

*   **Visual Theme:** Choose from a variety of ttkbootstrap themes.
*   **AI Generation:** Configure the maximum number of AI-generated capabilities, range for first-level capabilities, and select prompt templates for different operations.
*   **Model Selection:** Select the LLM model to be used for AI features.
*   **Layout:** Adjust layout algorithm, root font size, box dimensions, gaps, padding, target aspect ratio, and maximum level for visualization.
*   **Coloring:** Customize the color scheme for different capability levels and leaf nodes in the visualizer.

### User Directory and Template Customization

PyBCM creates a `.pybcm` directory in your home folder to store user-specific data and customizations:

```
~/.pybcm/
├── .env              # Environment configuration
├── settings.json     # User settings  
├── templates/        # Customizable templates
│   ├── chat.html            # Chat interface template
│   ├── expansion_prompt.j2  # AI capability expansion prompt
│   ├── first_level_prompt.j2# First-level capabilities prompt
│   └── system_prompt.j2     # AI system prompt
```

#### Template Customization

You can customize how PyBCM generates capabilities and displays the chat interface by modifying the templates in `~/.pybcm/templates/`:

1. **AI Prompts:**
   - `expansion_prompt.j2`: Customize how the AI generates sub-capabilities
   - `first_level_prompt.j2`: Modify the prompt for generating first-level capabilities
   - `system_prompt.j2`: Adjust the AI system prompt for better domain-specific responses

2. **Chat Interface:**
   - `chat.html`: Customize the appearance and behavior of the AI chat interface

The application will:
1. Create these templates automatically on first run
2. Use your customized versions if they exist
3. Fall back to the built-in templates if a customized version doesn't exist

You can select which templates to use for different operations through the Settings dialog:
1. Open Settings (File > Settings)
2. Go to the "AI Generation" tab
3. Choose templates from the dropdown menus:
   - "First-level generation template": Template for generating initial capabilities
   - "Normal generation template": Template for expanding existing capabilities

This allows you to:
- Tailor the AI prompts for your specific industry or use case
- Customize the chat interface appearance
- Experiment with different prompt strategies
- Switch between different prompt templates without editing files
- Maintain multiple template versions for different use cases
- Maintain your customizations across application updates

## Development

### Technologies Used

*   **Frontend:**
    *   [ttkbootstrap](https://ttkbootstrap.readthedocs.io/): Modern, themed Tkinter widgets.
    *   [tkinterweb](https://github.com/Andereoo/Tkinterweb): HTML rendering for rich text display.
*   **Backend:**
    *   [SQLAlchemy](https://www.sqlalchemy.org/): Database ORM for interacting with SQLite.
    *   [Pydantic](https://docs.pydantic.dev/): Data validation and settings management.
    *   [PydanticAI](https://github.com/e-dang/pydantic_ai): AI agent based on Pydantic models.
*   **AI:**
    *   [PydanticAI](https://github.com/pydantic/pydantic-ai): Agent framework for LLM interactions
    *   Supported LLM providers:
        - OpenAI (default)
        - Anthropic
        - Google AI (Gemini)
        - Groq
        - Mistral
        - Ollama
*   **Visualization:**
    *   Custom layout algorithms implemented in `layout.py` and `hq_layout.py`.
    *   `tkinter` Canvas for rendering.
*   **Export:**
    *   `svgwrite` (implicitly used for SVG generation)
    *   `python-pptx` for PowerPoint generation.
    *   `xml.etree.ElementTree` for Archimate XML generation.
*   **Other:**
    *   `uv`: Fast package manager for installing dependencies.
    *   `jinja2`: Templating engine for generating prompts and reports.
    *   `markdown`: For Markdown rendering in descriptions and AI chat.
    *   `logfire`: For logging and instrumentation.

### Contributing

Contributions are welcome! If you want to contribute to PyBCM, please follow these steps:

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Make your changes and write unit tests if applicable.
4. Ensure all tests pass and the code follows the project's style guide (we use `black`).
5. Submit a pull request with a clear description of your changes.

## License

PyBCM is released under the [MIT License](https://opensource.org/licenses/MIT).

## Acknowledgements

*   Thanks to the developers of all the open-source libraries used in this project.
*   Special thanks to [ttkbootstrap](https://github.com/israel-dryer/ttkbootstrap) for providing a fantastic set of modern Tkinter themes and widgets.

## Contact

For any questions or feedback, please open an issue on the [GitHub repository](https://github.com/ThomasRohde/PyBCM).

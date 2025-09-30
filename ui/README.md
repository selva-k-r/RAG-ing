# UI Module - Modular FastAPI Architecture

This directory contains the reorganized UI components following best practices for FastAPI application structure.

## 📁 Directory Structure

```
ui/
├── app.py                 # Main FastAPI application entry point
├── api/                   # API routes and handlers
│   ├── __init__.py
│   ├── routes.py          # API endpoints (/api/*)
│   └── pages.py           # HTML page routes (/, /result/*)
├── templates/             # Jinja2 HTML templates
│   └── home.html          # Main search interface
├── static/                # Static assets
│   ├── css/
│   │   └── main.css       # Main stylesheet
│   └── js/
│       └── main.js        # Frontend JavaScript
└── README.md              # This file
```

## 🎯 Architecture Benefits

### **Modular Design**
- **Separation of Concerns**: API logic separated from page rendering
- **Maintainability**: Easy to find and modify specific functionality
- **Scalability**: Can easily add new routes, templates, or static assets

### **FastAPI Best Practices**
- **Dependency Injection**: RAG system accessible throughout the app
- **Type Safety**: Pydantic models for request/response validation
- **Auto Documentation**: API docs automatically generated at `/docs`
- **Static File Serving**: Efficient serving of CSS/JS/images

### **Frontend Organization**
- **Template System**: Jinja2 templates for dynamic HTML generation
- **Static Assets**: Organized CSS and JavaScript files
- **Modern CSS**: CSS custom properties, responsive design, dark mode support
- **Progressive Enhancement**: JavaScript enhances but doesn't replace basic functionality

## 🚀 Key Components

### **app.py** - Main Application
- FastAPI app initialization
- Lifespan management for RAG system
- Route registration
- Static file mounting

### **api/routes.py** - API Endpoints
- `/api/search` - Process search queries
- `/api/health` - System health check
- `/api/status` - Detailed system status
- `/api/results/{id}` - Get cached search results
- `/api/feedback` - Submit user feedback

### **api/pages.py** - HTML Pages
- `/` - Main search interface
- `/result/{id}` - Detailed search result page

### **templates/home.html** - Search Interface
- Clean, modern search form
- Real-time result display
- Audience toggle (clinical/technical)
- Source attribution and confidence scoring

### **static/css/main.css** - Styling
- Modern CSS with custom properties
- Responsive design for mobile/desktop
- Dark mode support
- Consistent design system

### **static/js/main.js** - Frontend Logic
- AJAX search requests
- Dynamic result rendering
- Error handling
- Utility functions

## 🔄 Usage

### **Development Server**
```bash
# From project root
python ui/app.py

# Or via main CLI
python main.py --ui
```

### **Adding New Routes**
1. Add API routes to `api/routes.py`
2. Add page routes to `api/pages.py`
3. Register routers in `app.py`

### **Adding New Templates**
1. Create HTML files in `templates/`
2. Reference in page routes
3. Link static assets using `/static/`

### **Customizing Styles**
1. Edit `static/css/main.css`
2. Add new CSS files and link in templates
3. Use CSS custom properties for consistency

## 🔗 Integration with RAG System

The UI components integrate seamlessly with the core RAG system:

- **RAG Orchestrator**: Initialized on app startup
- **Query Processing**: Real-time search through RAG modules
- **Result Caching**: Temporary storage for detailed views
- **Feedback Loop**: User feedback passed back to evaluation module
- **Health Monitoring**: System status and metrics exposed

## 📝 Migration Notes

This modular structure replaces the previous monolithic `web_app.py` approach:

**Old Structure:**
- Single large file with all functionality
- Mixed concerns (API + HTML generation + static content)
- Harder to maintain and extend

**New Structure:**
- Clear separation of API routes, page routes, and static assets
- Easier to test individual components
- Better code organization and reusability
- Follows FastAPI and web development best practices

## 🎨 Frontend Features

- **Responsive Design**: Works on desktop and mobile devices
- **Progressive Enhancement**: Core functionality works without JavaScript
- **Accessibility**: Semantic HTML and keyboard navigation
- **Performance**: Optimized CSS and JavaScript loading
- **User Experience**: Clear feedback, loading states, and error handling

This architecture provides a solid foundation for future UI enhancements while maintaining clean, maintainable code.
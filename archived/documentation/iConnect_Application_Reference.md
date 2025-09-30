# iConnect - AI-Powered Search Application Reference

## Application Overview
**iConnect** is an AI-powered search interface designed for the IntegraConnect. It provides intelligent search capabilities across multiple data sources with contextual FAQ responses and detailed answer pages.

## Core Features

### 1. **Main Search Interface** (`home.html`)
- **Clean, modern UI** with gradient branding (blue to teal)
- **Multi-source search** with toggleable data source filters:
  - 📄 Confluence (active by default)
  - 🎫 Jira (active by default) 
  - 🏢 Internal Sites (active by default)
  - ☁️ Salesforce (active by default)
  - 🌍 External Sites (inactive by default)
- **Animated search bar** with rotating placeholder suggestions
- **FAQ section** with 5 pre-configured questions linking to detailed pages
- **User avatar** in top-right corner
- **Responsive design** with fixed header and scrollable content

### 2. **FAQ Response Pages** (faq1-5.html)
Each FAQ page follows a consistent structure:
- **Header** with home button and mini-search functionality
- **Question display** with shimmer animation effects
- **AI response** with confidence badges and detailed answers
- **Sources section** with clickable references
- **Interactive elements** (buttons, clarification options)

## FAQ Content Summary

| Page | Question | Key Features |
|------|----------|--------------|
| **FAQ1** | Pipeline xyz issue | DevOps ticket template generation, reference to similar resolved tickets |
| **FAQ2** | Anthem quality measure source | Data flow diagrams, technical details, source table mapping |
| **FAQ3** | PopHealth team setup | Step-by-step onboarding guide, code snippets, DevOps ticket requirements |
| **FAQ4** | FISH testing curation | Validation tables, step-by-step guidelines, curation checklists |
| **FAQ5** | Lymphadenopathy curation | Multi-context detection, disease-specific rules (CLL vs Breast Cancer) |

## Technical Architecture

### **Frontend Technology**
- Pure HTML/CSS/JavaScript (no frameworks)
- CSS Grid and Flexbox for layouts
- CSS animations and transitions
- Responsive design principles

### **Design System**
- **Primary Colors**: Blue (#1e88e5) to Teal (#26a69a) gradients
- **Typography**: Segoe UI font family
- **Layout**: Fixed header (50vh) with scrollable content below
- **Animations**: Shimmer effects, hover transitions, gradient animations

### **User Experience Features**
- **Search placeholder rotation** every 3 seconds
- **Source filter toggles** with visual feedback
- **Confidence badges** on AI responses (92-97% range)
- **Interactive elements** with hover effects and scaling
- **Breadcrumb navigation** via home button

## Data Sources & Context

### **Primary Data Sources**
- **Confluence**: Documentation and SOPs
- **Jira**: Tickets and issue tracking
- **Internal Sites**: Company-specific resources
- **Salesforce**: CRM data
- **External Sites**: Third-party references

### **Domain Expertise Areas**
- **Clinical Data Curation** (FISH testing, lymphadenopathy)
- **Quality Measures** (Anthem metrics, treatment plans)
- **Pipeline Operations** (DevOps, access management)
- **Team Onboarding** (PopHealth setup, DBT configuration)
- **Disease-Specific SOPs** (CLL/SLL, Breast Cancer)

## Key Use Cases

### 1. **Clinical Curation Support**
- FISH testing result validation
- Disease-specific curation rules
- Scan result interpretation
- Karyotype availability checking

### 2. **Technical Troubleshooting**
- Pipeline error resolution
- Access permission requests
- DevOps ticket generation
- System setup guidance

### 3. **Data Analysis**
- Quality measure source tracking
- Data flow documentation
- Schema relationship mapping
- Transformation logic explanation

### 4. **Team Operations**
- Onboarding new team members
- Environment setup procedures
- Tool installation guides
- Team communication channels

## Response Patterns

### **High Confidence Responses (94-97%)**
- Direct answers with specific source references
- Step-by-step procedures
- Clear action items

### **Multi-Context Responses (92%)**
- Ambiguity detection and clarification requests
- Disease-specific rule differentiation
- Context-dependent guidance

### **Template Generation**
- DevOps ticket templates
- Structured procedural guides
- Validation checklists
- Setup instructions

## Integration Points

### **Potential Backend Services**
- Confluence API for documentation search
- Jira API for ticket management
- Snowflake database for data queries
- DBT for transformation logic
- Git repositories for code references

### **Authentication & Access**
- User avatar suggests user management
- Source filtering implies permission-based access
- DevOps ticket creation suggests workflow integration

## Styling & Branding Guidelines

### **Color Palette**
- Primary: #1e88e5 (Blue)
- Secondary: #26a69a (Teal)
- Success: #4caf50 (Green)
- Warning: #ff9800 (Orange)
- Error: #f44336 (Red)
- Purple accents: #9c27b0

### **Layout Constants**
- Header height: 50vh
- Content margin: 51vh
- Search width: 650px
- FAQ width: 80%
- Border radius: 8-16px for cards

### **Animation Timing**
- Shimmer effects: 4s infinite
- Hover transitions: 0.3s ease
- Placeholder rotation: 3s intervals

## Future Enhancement Opportunities
- Real-time search suggestions
- Advanced filtering options
- User preference management
- Search history tracking
- Integration with more data sources
- Mobile app version
- Voice search capabilities
- Collaborative features (sharing, commenting)

---

**Application Purpose**: Streamline information discovery and problem-solving for PopHealth team members through intelligent, context-aware search and response generation.

**Target Users**: Clinical data curators, data analysts, DevOps engineers, new team members, and PopHealth domain experts.

**Key Value Proposition**: Reduces time-to-resolution for common questions and provides consistent, high-quality responses with proper source attribution and actionable next steps.

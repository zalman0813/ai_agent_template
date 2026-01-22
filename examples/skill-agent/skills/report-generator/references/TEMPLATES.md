# Report Generator Template System

## Overview

The Report Generator supports custom HTML templates to create branded, professional reports. Templates use a simple placeholder system that gets replaced with actual content during report generation.

## Template Placeholders

Templates must include these four required placeholders:

### `{{TITLE}}`
The report title specified via the `--title` parameter.

**Example**: `<h1>{{TITLE}}</h1>`

### `{{TIMESTAMP}}`
The generation timestamp in format: `YYYY-MM-DD HH:MM:SS`

**Example**: `<div class="timestamp">Generated: {{TIMESTAMP}}</div>`

### `{{SUMMARY}}`
The summary section containing:
- Total record count
- Statistics for numeric fields (sum, average, min, max)
- Formatted as HTML with stat-card divs

**Example**:
```html
<div class="summary-section">
  <h2>Summary</h2>
  {{SUMMARY}}
</div>
```

### `{{DATA}}`
The main data table containing all records, formatted as an HTML table with:
- `<thead>` with column headers
- `<tbody>` with data rows

**Example**:
```html
<div class="data-section">
  <h2>Data</h2>
  {{DATA}}
</div>
```

## Template Requirements

### Required Elements
1. All four placeholders must be present
2. Valid HTML structure (DOCTYPE, html, head, body tags)
3. UTF-8 character encoding declaration
4. Viewport meta tag for responsive design (recommended)

### Styling Recommendations
- Include embedded CSS in `<style>` tags for portability
- Make tables responsive with proper width and overflow handling
- Use readable fonts and sufficient contrast
- Support both screen and print media
- Consider mobile/tablet viewports

### CSS Class Names
When the generator creates summary and data elements, it uses these class names that you can style:

- `.stat-card` - Individual statistic cards
- `.stat-card h4` - Statistic field name
- `.stat-card p` - Statistic values
- `table` - Data table
- `th` - Table headers
- `td` - Table cells
- `tr:nth-child(even)` - Even rows (for alternating colors)
- `tr:hover` - Row hover state

## Creating Custom Templates

### Step 1: Start with Base HTML Structure

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{TITLE}}</title>
    <style>
        /* Your custom styles here */
    </style>
</head>
<body>
    <!-- Your template layout here -->
</body>
</html>
```

### Step 2: Add Required Placeholders

```html
<body>
    <header>
        <h1>{{TITLE}}</h1>
        <p class="timestamp">Generated: {{TIMESTAMP}}</p>
    </header>

    <section class="summary">
        {{SUMMARY}}
    </section>

    <section class="data">
        {{DATA}}
    </section>
</body>
```

### Step 3: Add Custom Styling

Customize colors, fonts, layouts, and responsive behavior:

```css
body {
    font-family: 'Helvetica Neue', Arial, sans-serif;
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
    background: linear-gradient(to bottom, #f5f7fa, #c3cfe2);
}

header {
    background: white;
    padding: 30px;
    border-radius: 10px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    margin-bottom: 20px;
}

/* More custom styles... */
```

### Step 4: Save and Use

Save your template in the `references/` directory and use it:

```bash
python3 /skills/report-generator/scripts/generate_report.py \
  --input /workspace/data.json \
  --output /workspace/report.html \
  --format html \
  --template /skills/report-generator/references/my_custom_template.html
```

## Example Templates

### Minimal Template

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{{TITLE}}</title>
</head>
<body>
    <h1>{{TITLE}}</h1>
    <p><em>{{TIMESTAMP}}</em></p>
    <div>{{SUMMARY}}</div>
    <div>{{DATA}}</div>
</body>
</html>
```

### Professional Template

See `report_template.html` in this directory for a complete professional template with:
- Responsive grid layout
- Color-coded statistics cards
- Styled tables with hover effects
- Print-friendly CSS
- Mobile-optimized design

## Template Testing

### Validation Checklist

Before using a custom template, verify:

- [ ] All four placeholders are present
- [ ] HTML is valid (use W3C validator)
- [ ] UTF-8 encoding is specified
- [ ] CSS is embedded (no external stylesheets)
- [ ] Template renders correctly without data (placeholders visible)
- [ ] Responsive design works on mobile/tablet/desktop
- [ ] Print layout is acceptable

### Testing Process

1. Create a small test dataset (5-10 records)
2. Generate a report with your template
3. Open the output HTML in multiple browsers
4. Test responsive behavior (resize window)
5. Test print preview (Ctrl/Cmd+P)
6. Verify all data displays correctly

## Troubleshooting

### Missing Placeholder Error

**Error**: `Template missing required placeholders: {{TITLE}}, {{DATA}}`

**Solution**: Ensure all four placeholders are present in your template. Check for typos in placeholder names.

### Template Not Loading

**Error**: `Template file not found: /path/to/template.html`

**Solution**: Verify the template path is correct. Use absolute paths starting with `/skills/report-generator/references/`.

### Styling Not Applied

**Issue**: Template loads but styling doesn't work.

**Solution**:
- Ensure CSS is in `<style>` tags, not external files
- Check for CSS syntax errors
- Verify class names match generated elements

### Data Not Displaying

**Issue**: Placeholders remain unreplaced in output.

**Solution**:
- Check placeholder syntax (must be uppercase with double braces)
- Ensure no extra spaces: `{{DATA}}` not `{{ DATA }}`
- Verify template file encoding is UTF-8

## Best Practices

1. **Keep It Simple**: Complex templates with JavaScript may not work well with generated content
2. **Test Early**: Test your template with sample data before using in production
3. **Mobile First**: Design for mobile screens first, then enhance for desktop
4. **Use Semantic HTML**: Proper heading hierarchy (h1, h2, h3) and semantic tags
5. **Accessible Design**: Sufficient color contrast, readable fonts, proper alt text
6. **Printable**: Include print media queries for paper output
7. **Self-Contained**: Embed all resources (CSS, small images as data URLs) for portability

## Advanced Techniques

### Responsive Tables

```css
@media (max-width: 768px) {
    table, thead, tbody, th, td, tr {
        display: block;
    }

    thead tr {
        position: absolute;
        top: -9999px;
        left: -9999px;
    }

    td {
        border: none;
        position: relative;
        padding-left: 50%;
    }

    td:before {
        content: attr(data-label);
        position: absolute;
        left: 6px;
        font-weight: bold;
    }
}
```

### Print Styles

```css
@media print {
    body {
        background: white;
        font-size: 10pt;
    }

    .no-print {
        display: none;
    }

    table {
        page-break-inside: avoid;
    }

    h1, h2 {
        page-break-after: avoid;
    }
}
```

### Dark Mode Support

```css
@media (prefers-color-scheme: dark) {
    body {
        background: #1a1a1a;
        color: #e0e0e0;
    }

    table {
        background: #2d2d2d;
    }

    th {
        background: #0d47a1;
    }
}
```

## Template Gallery

The `references/` directory includes these templates:

1. **report_template.html** - Professional default template
   - Clean, modern design
   - Responsive layout
   - Print-friendly
   - Statistics cards with color coding

*More templates can be added here by the community*

## Contributing Templates

To contribute a new template:

1. Create your template following the guidelines
2. Test thoroughly with various data sets
3. Document any special features or requirements
4. Submit to the `references/` directory
5. Update this documentation

## Resources

- [HTML5 Specification](https://html.spec.whatwg.org/)
- [CSS Grid Layout](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Grid_Layout)
- [Responsive Web Design](https://developer.mozilla.org/en-US/docs/Learn/CSS/CSS_layout/Responsive_Design)
- [Print CSS](https://www.smashingmagazine.com/2018/05/print-stylesheets-in-2018/)

## Version History

- **1.0.0**: Initial template system with four placeholders

"""
PDF Generator for Workflow Execution Reports

This module provides functionality to generate professional PDF reports
for workflow execution results. Reports are clean, neutral, and suitable
for end-clients without any vendor branding.

Key Features:
    - Professional formatting with headers, sections, and styling
    - Support for structured data (dictionaries, lists, nested objects)
    - Automatic page breaks for long content
    - Date/time stamping
    - Clean, neutral design suitable for any business
"""

from datetime import datetime
from io import BytesIO
from typing import Dict, Any, Optional
import json

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether
)
from reportlab.pdfgen import canvas


class PDFReportGenerator:
    """
    Generator for workflow execution PDF reports.

    Creates professional, well-formatted PDF documents containing
    workflow execution results in a clean, business-appropriate style.
    """

    def __init__(self):
        """Initialize PDF generator with default styles."""
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Create custom paragraph styles for the report."""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))

        # Section heading style
        self.styles.add(ParagraphStyle(
            name='SectionHeading',
            parent=self.styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=12,
            spaceBefore=20,
            fontName='Helvetica-Bold'
        ))

        # Subsection heading style
        self.styles.add(ParagraphStyle(
            name='SubHeading',
            parent=self.styles['Heading2'],
            fontSize=13,
            textColor=colors.HexColor('#34495e'),
            spaceAfter=8,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        ))

        # Body text style
        self.styles.add(ParagraphStyle(
            name='CustomBodyText',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=8,
            leading=14,
            fontName='Helvetica'
        ))

        # Footer style
        self.styles.add(ParagraphStyle(
            name='Footer',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#7f8c8d'),
            alignment=TA_CENTER,
            fontName='Helvetica-Oblique'
        ))

    def generate_report(
        self,
        workflow_name: str,
        workflow_description: str,
        execution_result: str,
        execution_status: str,
        execution_time: Optional[float] = None,
        execution_date: Optional[datetime] = None,
        workflow_id: Optional[str] = None,
        execution_id: Optional[str] = None
    ) -> BytesIO:
        """
        Generate a PDF report for a workflow execution.

        Args:
            workflow_name: Name of the workflow
            workflow_description: Description of what the workflow does
            execution_result: The result/output from workflow execution
            execution_status: Status of execution (success, failed, etc.)
            execution_time: Time taken to execute (in seconds)
            execution_date: When the workflow was executed
            workflow_id: Unique workflow identifier
            execution_id: Unique execution identifier

        Returns:
            BytesIO: PDF file as bytes buffer, ready to be sent to client
        """
        # Create buffer to hold PDF in memory
        buffer = BytesIO()

        # Create PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm,
            title=f"Workflow Execution Report - {workflow_name}",
            author="Workflow Automation System"
        )

        # Build story (content elements)
        story = []

        # Add title
        story.append(Paragraph("Workflow Execution Report", self.styles['CustomTitle']))
        story.append(Spacer(1, 0.5*cm))

        # Add execution date/time
        if execution_date:
            date_str = execution_date.strftime("%d/%m/%Y %H:%M:%S")
        else:
            date_str = datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S")

        story.append(Paragraph(
            f"<i>Generated on {date_str}</i>",
            self.styles['Footer']
        ))
        story.append(Spacer(1, 1*cm))

        # Section 1: Workflow Information
        story.append(Paragraph("Workflow Information", self.styles['SectionHeading']))

        workflow_info_data = [
            ["Workflow Name:", workflow_name or "Unnamed Workflow"],
            ["Description:", workflow_description or "No description provided"],
        ]

        if workflow_id:
            workflow_info_data.append(["Workflow ID:", workflow_id])
        if execution_id:
            workflow_info_data.append(["Execution ID:", execution_id])

        workflow_table = Table(workflow_info_data, colWidths=[4*cm, 13*cm])
        workflow_table.setStyle(TableStyle([
            ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 11),
            ('FONT', (1, 0), (1, -1), 'Helvetica', 11),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2c3e50')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))

        story.append(workflow_table)
        story.append(Spacer(1, 1*cm))

        # Section 2: Execution Status
        story.append(Paragraph("Execution Status", self.styles['SectionHeading']))

        # Status color based on result
        status_color = colors.HexColor('#27ae60') if execution_status.lower() in ['success', 'completed'] else colors.HexColor('#e74c3c')

        status_data = [
            ["Status:", execution_status.upper()],
        ]

        if execution_time is not None:
            status_data.append(["Execution Time:", f"{execution_time:.2f} seconds"])

        status_table = Table(status_data, colWidths=[4*cm, 13*cm])
        status_table.setStyle(TableStyle([
            ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 11),
            ('FONT', (1, 0), (1, -1), 'Helvetica-Bold', 11),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (1, 0), (1, 0), status_color),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))

        story.append(status_table)
        story.append(Spacer(1, 1*cm))

        # Section 3: Execution Results
        story.append(Paragraph("Execution Results", self.styles['SectionHeading']))
        story.append(Spacer(1, 0.3*cm))

        # Format results based on content type
        result_elements = self._format_result(execution_result)
        story.extend(result_elements)

        # Add footer
        story.append(Spacer(1, 2*cm))
        story.append(Paragraph(
            "<i>This report was automatically generated by the Workflow Automation System</i>",
            self.styles['Footer']
        ))

        # Build PDF
        doc.build(story)

        # Reset buffer position to beginning
        buffer.seek(0)

        return buffer

    def _format_result(self, result: str) -> list:
        """
        Format execution result for PDF display.

        Attempts to parse result as JSON for structured display,
        falls back to plain text if not JSON.

        Args:
            result: The execution result string

        Returns:
            List of ReportLab flowables (paragraphs, tables, etc.)
        """
        elements = []

        # Try to parse as JSON for better formatting
        try:
            result_data = json.loads(result)
            elements.extend(self._format_json_data(result_data))
        except (json.JSONDecodeError, TypeError):
            # Not JSON, display as plain text
            # Handle multi-line text
            lines = result.split('\n')
            for line in lines:
                if line.strip():
                    # Escape XML special characters
                    safe_line = (line
                                .replace('&', '&amp;')
                                .replace('<', '&lt;')
                                .replace('>', '&gt;'))
                    elements.append(Paragraph(safe_line, self.styles['CustomBodyText']))
                else:
                    elements.append(Spacer(1, 0.2*cm))

        return elements

    def _format_json_data(self, data: Any, level: int = 0) -> list:
        """
        Format JSON/dict data into readable PDF elements.

        Args:
            data: JSON data (dict, list, or primitive)
            level: Indentation level for nested data

        Returns:
            List of ReportLab flowables
        """
        elements = []
        indent = level * 0.5 * cm

        if isinstance(data, dict):
            # Create table for key-value pairs
            table_data = []
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    # Nested structure - display key and recurse
                    elements.append(Paragraph(
                        f"<b>{key}:</b>",
                        self.styles['SubHeading']
                    ))
                    elements.extend(self._format_json_data(value, level + 1))
                else:
                    # Simple key-value pair
                    table_data.append([str(key), str(value)])

            if table_data:
                # Create table for simple key-value pairs
                result_table = Table(table_data, colWidths=[5*cm, 12*cm])
                result_table.setStyle(TableStyle([
                    ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 11),
                    ('FONT', (1, 0), (1, -1), 'Helvetica', 11),
                    ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2c3e50')),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 8),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ecf0f1')),
                ]))
                elements.append(result_table)
                elements.append(Spacer(1, 0.5*cm))

        elif isinstance(data, list):
            for i, item in enumerate(data):
                elements.append(Paragraph(
                    f"<b>Item {i + 1}:</b>",
                    self.styles['CustomBodyText']
                ))
                elements.extend(self._format_json_data(item, level + 1))
                elements.append(Spacer(1, 0.3*cm))

        else:
            # Primitive value
            elements.append(Paragraph(str(data), self.styles['CustomBodyText']))

        return elements


# Singleton instance
pdf_generator = PDFReportGenerator()

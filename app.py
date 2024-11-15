import numpy as np
import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import pdfplumber

# Streamlit Page Configuration
st.set_page_config(
    page_title="PDF Text Extractor",
    layout="wide",
    initial_sidebar_state="expanded",
)


def load_pdf(pdf_file):
    """Load a PDF file with pdfplumber."""
    try:
        pdf = pdfplumber.open(pdf_file)
        return pdf
    except Exception as e:
        st.error(f"Failed to load PDF: {e}")
        return None


def extract_page_image(pdf, page_number, max_width=800, max_height=1000):
    """Extract and resize the image of a specific page from a PDF."""
    try:
        page = pdf.pages[page_number]
        image = page.to_image()
        img_pil = image.original

        # Resize the image to fit within max_width and max_height
        scale_factor = min(max_width / img_pil.width, max_height / img_pil.height)
        new_width = int(img_pil.width * scale_factor)
        new_height = int(img_pil.height * scale_factor)
        img_resized = img_pil.resize((new_width, new_height), Image.Resampling.LANCZOS)
        return img_resized, (new_width, new_height), (page.width, page.height)
    except Exception as e:
        st.error(f"Error processing page image: {e}")
        return None, None, None


def scale_bbox_to_pdf(bbox, canvas_dims, pdf_dims):
    """Scale the bounding box coordinates from canvas dimensions to PDF dimensions."""
    canvas_width, canvas_height = canvas_dims
    pdf_width, pdf_height = pdf_dims

    scale_x = pdf_width / canvas_width
    scale_y = pdf_height / canvas_height

    x0, y0, x1, y1 = bbox
    return (x0 * scale_x, y0 * scale_y, x1 * scale_x, y1 * scale_y)


def extract_text_from_pdf(pdf, scaled_bbox):
    """Extract text from all pages within the scaled bounding box."""
    all_text = ""
    for page_number, page in enumerate(pdf.pages, start=1):
        text = page.within_bbox(scaled_bbox).extract_text()
        if text:
            all_text += f"\n\n--- Page {page_number} ---\n{text}"
    return all_text


# Main App
def main():
    st.title("PDF Text Extractor")
    st.markdown("Upload a PDF, draw a bounding box, and extract text from the selected area.")

    # Sidebar for PDF upload and page selection
    st.sidebar.header("Upload your files here")
    uploaded_pdf = st.sidebar.file_uploader("Select a PDF", type=["pdf"])

    if uploaded_pdf:
        pdf = load_pdf(uploaded_pdf)

        if pdf:
            total_pages = len(pdf.pages)
            page_number = st.sidebar.slider("Select Page Number", 1, total_pages, 1) - 1

            # Extract and display page image
            img_pil, canvas_dims, pdf_dims = extract_page_image(pdf, page_number)
            if img_pil:
                st.write(f"Page {page_number + 1}: Draw a bounding box to select text")
                canvas_result = st_canvas(
                    fill_color=None,  # Transparent fill # type: ignore
                    stroke_width=2,
                    stroke_color="#FF0000",  # Red outline for bounding box
                    background_image=img_pil, # type: ignore
                    update_streamlit=True,
                    width=canvas_dims[0], # type: ignore
                    height=canvas_dims[1], # type: ignore
                    drawing_mode="rect",
                    key="canvas",
                )

                # Process bounding box
                if canvas_result.json_data and canvas_result.json_data["objects"]:
                    last_object = canvas_result.json_data["objects"][-1]
                    x0, y0 = last_object["left"], last_object["top"]
                    x1, y1 = x0 + last_object["width"], y0 + last_object["height"]

                    st.write("Bounding Box Coordinates")
                    st.write(f"Top-left: ({x0:.1f}, {y0:.1f}) | Bottom-right: ({x1:.1f}, {y1:.1f})")

                    # Scale bounding box to PDF dimensions
                    scaled_bbox = scale_bbox_to_pdf((x0, y0, x1, y1), canvas_dims, pdf_dims)

                    # Extract text
                    with st.spinner("Extracting text from PDF..."):
                        extracted_text = extract_text_from_pdf(pdf, scaled_bbox)

                    if extracted_text.strip():
                        st.write("Extracted Text")
                        st.text_area("Text from the selected area:", extracted_text, height=300)
                        st.download_button(
                            label="Download Extracted Text",
                            data=extracted_text,
                            file_name="extracted_text.txt",
                            mime="text/plain",
                        )
                    else:
                        st.warning("No text found in the selected area across all pages.")
                else:
                    st.info("Draw a bounding box to select text.")
            else:
                st.error("Failed to process the selected page.")
        else:
            st.error("Invalid PDF file. Please try again.")
    else:
        st.info("Upload a PDF file to start extracting text.")


if __name__ == "__main__":
    main()
import logfire

logfire.configure(send_to_logfire=False)


def parse_langchain_html(file_path: str) -> str:
    from langchain_community.document_loaders import UnstructuredHTMLLoader

    with logfire.span("LangChain HTML Parsing", filename=file_path):
        try:
            loader = UnstructuredHTMLLoader(file_path)
            documents = loader.load()
            return "\n".join(doc.page_content for doc in documents)

        except Exception:
            logfire.exception("Error parsing HTML file")
            return ""


if __name__ == "__main__":

    file_path = "../../../DATA/true_data/payment_issue.html"
    text = parse_langchain_html(file_path)
    print(text)
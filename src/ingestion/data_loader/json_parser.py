from langchain_community.document_loaders import JSONLoader
import logfire

logfire.configure(send_to_logfire=False)


def json_loader(file_name: str):
    with logfire.span("json_parse", filename=file_name):
        try:
            loader = JSONLoader(
                file_path=file_name,
                jq_schema=".[]",
                text_content=False
            )

            documents = loader.load()

            return "\n".join(
                [doc.page_content for doc in documents]
            )

        except Exception as e:
            logfire.error(f"Error parsing JSON file {file_name}: {e}")
            return ""


if __name__ == "__main__":

    file_name = "../../../DATA/true_data/product.json"

    text = json_loader(file_name)

    print(text)
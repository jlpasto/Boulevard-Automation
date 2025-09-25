import base64

with open("the-colony-kdt-webform-9eb44187396a.json", "r", encoding="utf-8") as f:
    data = f.read()

encoded_data = base64.b64encode(data.encode("utf-8")).decode("utf-8")

with open("encoded_credentials.txt", "w", encoding="utf-8") as out:
    out.write(encoded_data)
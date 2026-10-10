/** Read a File/Blob as UTF-8 text. Uses FileReader so it works in browsers and jsdom alike. */
export function readFileText(file: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(typeof reader.result === "string" ? reader.result : "");
    reader.onerror = () => reject(reader.error ?? new Error("Could not read the file"));
    reader.readAsText(file, "utf-8");
  });
}

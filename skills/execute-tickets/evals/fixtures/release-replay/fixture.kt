// Read-only excerpt from a release verification fixture.
fun writeResult(application: Application, invocation: String, result: String) {
    File(application.filesDir, "embedding-$invocation.json").writeText(result)
}

using namespace Windows.Storage
using namespace Windows.Data.Pdf
using namespace Windows.Storage.Streams

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime

function Await-Operation {
    param($Operation, [Type]$ResultType)
    $method = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
        $_.Name -eq 'AsTask' -and $_.IsGenericMethodDefinition -and
        $_.GetGenericArguments().Count -eq 1 -and $_.GetParameters().Count -eq 1
    } | Select-Object -First 1
    $task = $method.MakeGenericMethod($ResultType).Invoke($null, @($Operation))
    $task.GetAwaiter().GetResult()
}

function Await-Action {
    param($Action)
    $method = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
        $_.Name -eq 'AsTask' -and -not $_.IsGenericMethodDefinition -and $_.GetParameters().Count -eq 1
    } | Select-Object -First 1
    $method.Invoke($null, @($Action)).GetAwaiter().GetResult()
}

$input = 'C:\Users\wansi\Downloads\DECLARATION AOUT.pdf'
$outDir = 'D:\instances_odoo\le_jardinier\addons\primetech_tax_automation\tmp\pdfs\declaration_aout'
New-Item -ItemType Directory -Path $outDir -Force | Out-Null

$storageFileType = [Windows.Storage.StorageFile,Windows.Storage,ContentType=WindowsRuntime]
$pdfDocumentType = [Windows.Data.Pdf.PdfDocument,Windows.Data,ContentType=WindowsRuntime]
$asyncDefinition = [Windows.Foundation.IAsyncOperation`1,Windows.Foundation,ContentType=WindowsRuntime]
$file = Await-Operation ($storageFileType::GetFileFromPathAsync($input)) $storageFileType
$pdf = Await-Operation ($pdfDocumentType::LoadFromFileAsync($file)) $pdfDocumentType
$streamType = [Windows.Storage.Streams.InMemoryRandomAccessStream,Windows.Storage,ContentType=WindowsRuntime]
$readerType = [Windows.Storage.Streams.DataReader,Windows.Storage,ContentType=WindowsRuntime]

for ($index = 0; $index -lt $pdf.PageCount; $index++) {
    $page = $pdf.GetPage($index)
    $stream = [Activator]::CreateInstance($streamType)
    Await-Action ($page.RenderToStreamAsync($stream))
    $reader = [Activator]::CreateInstance($readerType, @($stream.GetInputStreamAt(0)))
    $sizeOperationType = $asyncDefinition.MakeGenericType([UInt32])
    $count = Await-Operation ($reader.LoadAsync([UInt32]$stream.Size)) ([UInt32])
    $bytes = New-Object byte[] $count
    $reader.ReadBytes($bytes)
    $png = Join-Path $outDir ('page-{0:D2}.png' -f ($index + 1))
    [System.IO.File]::WriteAllBytes($png, $bytes)
}

Write-Output "PAGE_COUNT=$($pdf.PageCount)"
Write-Output "OUTPUT_DIR=$outDir"

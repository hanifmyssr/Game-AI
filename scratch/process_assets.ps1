$code = @"
using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;
using System.Collections.Generic;

public class ImageProcessor
{
    public static void ProcessImage(string srcPath, string destPath, int threshold, int targetSize)
    {
        using (Bitmap src = new Bitmap(srcPath))
        {
            Bitmap resized = new Bitmap(targetSize, targetSize, PixelFormat.Format32bppArgb);
            using (Graphics g = Graphics.FromImage(resized))
            {
                g.InterpolationMode = System.Drawing.Drawing2D.InterpolationMode.HighQualityBicubic;
                g.SmoothingMode = System.Drawing.Drawing2D.SmoothingMode.HighQuality;
                g.PixelOffsetMode = System.Drawing.Drawing2D.PixelOffsetMode.HighQuality;
                g.DrawImage(src, 0, 0, targetSize, targetSize);
            }

            int w = resized.Width;
            int h = resized.Height;
            BitmapData data = resized.LockBits(new Rectangle(0, 0, w, h), ImageLockMode.ReadWrite, PixelFormat.Format32bppArgb);
            int byteCount = data.Stride * h;
            byte[] bytes = new byte[byteCount];
            Marshal.Copy(data.Scan0, bytes, 0, byteCount);

            bool[] visited = new bool[w * h];
            Queue<int> queue = new Queue<int>();

            for (int x = 0; x < w; x++)
            {
                TryEnqueue(x, 0, w, h, bytes, data.Stride, threshold, visited, queue);
                TryEnqueue(x, h - 1, w, h, bytes, data.Stride, threshold, visited, queue);
            }
            for (int y = 0; y < h; y++)
            {
                TryEnqueue(0, y, w, h, bytes, data.Stride, threshold, visited, queue);
                TryEnqueue(w - 1, y, w, h, bytes, data.Stride, threshold, visited, queue);
            }

            int[] dx = { 0, 0, 1, -1 };
            int[] dy = { 1, -1, 0, 0 };

            while (queue.Count > 0)
            {
                int curr = queue.Dequeue();
                int cx = curr % w;
                int cy = curr / w;

                int idx = cy * data.Stride + cx * 4;
                bytes[idx + 3] = 0; // Alpha = 0 (Transparent)

                for (int i = 0; i < 4; i++)
                {
                    int nx = cx + dx[i];
                    int ny = cy + dy[i];
                    if (nx >= 0 && nx < w && ny >= 0 && ny < h)
                    {
                        TryEnqueue(nx, ny, w, h, bytes, data.Stride, threshold, visited, queue);
                    }
                }
            }

            Marshal.Copy(bytes, 0, data.Scan0, byteCount);
            resized.UnlockBits(data);
            resized.Save(destPath, ImageFormat.Png);
            resized.Dispose();
        }
    }

    private static void TryEnqueue(int x, int y, int w, int h, byte[] bytes, int stride, int threshold, bool[] visited, Queue<int> queue)
    {
        int p = y * w + x;
        if (visited[p]) return;
        visited[p] = true;

        int idx = y * stride + x * 4;
        byte b = bytes[idx];
        byte g = bytes[idx + 1];
        byte r = bytes[idx + 2];

        if (r <= threshold && g <= threshold && b <= threshold)
        {
            queue.Enqueue(p);
        }
    }
}
"@

Add-Type -TypeDefinition $code -ReferencedAssemblies System.Drawing

$brainDir = "C:\Users\Pavilion\.gemini\antigravity-ide\brain\b2b19d09-f4cb-4521-818a-3ed71602630e"
$itemsDir = "assets\items"
$portraitsDir = "assets\portraits"

$assets = @(
    @{ Src = "$brainDir\health_potion_1791273602631.jpg"; Dest = "$itemsDir\health_potion.png"; Size = 128; Thresh = 30 },
    @{ Src = "$brainDir\mega_potion_1791273630268.jpg";   Dest = "$itemsDir\mega_potion.png";   Size = 128; Thresh = 30 },
    @{ Src = "$brainDir\item_sword_1791273667141.jpg";    Dest = "$itemsDir\item_sword.png";    Size = 128; Thresh = 30 },
    @{ Src = "$brainDir\item_shield_1791273690895.jpg";   Dest = "$itemsDir\item_shield.png";   Size = 128; Thresh = 30 },
    @{ Src = "$brainDir\item_boots_1791273717645.jpg";    Dest = "$itemsDir\item_boots.png";    Size = 128; Thresh = 30 },
    @{ Src = "$brainDir\portrait_warrior_1791273742989.jpg"; Dest = "$portraitsDir\portrait_warrior.png"; Size = 256; Thresh = 30 },
    @{ Src = "$brainDir\portrait_mage_1791273767699.jpg";    Dest = "$portraitsDir\portrait_mage.png";    Size = 256; Thresh = 30 },
    @{ Src = "$brainDir\portrait_ranger_1791273802122.jpg";  Dest = "$portraitsDir\portrait_ranger.png";  Size = 256; Thresh = 30 }
)

foreach ($item in $assets) {
    Write-Output "Processing $($item.Dest)..."
    [ImageProcessor]::ProcessImage($item.Src, $item.Dest, $item.Thresh, $item.Size)
}

Write-Output "ALL ASSETS PROCESSED SUCCESSFULLY!"

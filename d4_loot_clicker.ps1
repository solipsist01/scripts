#backspace for fast looting. (left click spam) ctrl+backspace for fast obol gambling (right click spam)

if (-not ("FastClickerPS" -as [type])) {

Add-Type @"
using System;
using System.Runtime.InteropServices;

public class FastClickerPS
{
    [DllImport("user32.dll")]
    public static extern void mouse_event(
        uint flags,
        uint dx,
        uint dy,
        uint data,
        UIntPtr extra
    );

    [DllImport("user32.dll")]
    public static extern short GetAsyncKeyState(int key);


    public const uint LEFTDOWN  = 0x0002;
    public const uint LEFTUP    = 0x0004;

    public const uint RIGHTDOWN = 0x0008;
    public const uint RIGHTUP   = 0x0010;


    public static void MouseDown(bool right)
    {
        mouse_event(
            right ? RIGHTDOWN : LEFTDOWN,
            0, 0, 0, UIntPtr.Zero
        );
    }


    public static void MouseUp(bool right)
    {
        mouse_event(
            right ? RIGHTUP : LEFTUP,
            0, 0, 0, UIntPtr.Zero
        );
    }
}
"@

}


$BACKSPACE = 0x08
$LCTRL = 0xA2
$RCTRL = 0xA3


$clicking = $false
$last = [Environment]::TickCount
$state = $false
$rightClick = $false


Write-Host "Hold Backspace = left click"
Write-Host "Hold Ctrl + Backspace = right click"


while ($true)
{
    $back =
        ([FastClickerPS]::GetAsyncKeyState($BACKSPACE) -band 0x8000)

    $ctrl =
        (([FastClickerPS]::GetAsyncKeyState($LCTRL) -band 0x8000) -or
         ([FastClickerPS]::GetAsyncKeyState($RCTRL) -band 0x8000))


    if ($back)
    {
        if (-not $clicking)
        {
            $clicking = $true
            $state = $false
            $rightClick = $ctrl
        }


        if (([Environment]::TickCount - $last) -ge 50)
        {
            if ($state)
            {
                [FastClickerPS]::MouseUp($rightClick)
            }
            else
            {
                [FastClickerPS]::MouseDown($rightClick)
            }

            $state = !$state
            $last = [Environment]::TickCount
        }
    }
    else
    {
        if ($state)
        {
            [FastClickerPS]::MouseUp($rightClick)
        }

        $clicking = $false
        $state = $false
    }
    Start-Sleep -Milliseconds 1
}
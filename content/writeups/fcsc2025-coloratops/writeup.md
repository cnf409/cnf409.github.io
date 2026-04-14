+++
type             = "ctf"
title            = "coloratops"
description      = "Voici un crackme plein de couleurs avec des allures old school."
author           = "conflict"
date             = "2025-04-27"
language         = "fr"
tags             = ["reverse", "gdb", "crackme"]
event            = "FCSC 2025"
category         = "reverse"
stars            = 2
challenge_author = "unknown"
solves           = ?
rating           = 9

+++

## Note

Writeup d'un challenge de _reverse_ du FCSC 2025. Ce challenge était un crackme classique, avec un petit twist coloré...

## Description

```text
Voici un crackme plein de couleurs avec des allures old school.
```

## Analyse initiale

### Informations

On nous donne un exécutable:

```css
file coloratops;
coloratops: ELF 64-bit LSB pie executable, x86-64, version 1 (SYSV), dynamically linked, interpreter /lib64/ld-linux-x86-64.so.2, BuildID[sha1]=34ce7dda6332fe818a86eb6f98df9610f088e6da, for GNU/Linux 3.2.0, stripped
```

On est sur un ELF en 64 bits, qui est strippé.

![me_when_elf_is_stripped.jpg](https://i.ibb.co/j996X9Yn/me-when-elf-is-stripped.jpg)

### Identification des fonctions principales et nommage

Après avoir identifié la fonction main depuis l'appel à `__libc_start_main`, on voit plusieurs points clés:

- Création de la fenêtre et de son *renderer*:

```c
window = SDL_CreateWindow("FCSC 2025 - Coloratops",0x2fff0000,0x2fff0000,0x4b0,0x2ae,0x14);
if (window == 0) {
  TTF_Quit();
  SDL_Quit();
  uVar3 = 1;
}
else {
  renderer = SDL_CreateRenderer(window,0xffffffff,6);
  if (renderer == 0) {
    uVar3 = 1;
  }
```

- Création des éléments audio:

```c
audioCallback = FUN_00109f01;
userData = 0;
audioDeviceId = SDL_OpenAudioDevice(0,0,&wantedSpec,&obtainedSpec,0xb);
loadInitialTextures(renderer,&font);
```

- Début de la boucle principale et de la boucle de gestion des événements:

```c
isRunning = 1;
startTicks = SDL_GetTicks();
while (isRunning != 0) {
  while (sdlResult = SDL_PollEvent(eventBuffer), sdlResult != 0) {
```

### Les événements disponibles

On voit plusieurs évènements possibles pour le programme:

- `0x100` - _SDL_QUIT_: Quitte le programme
```c
if (eventBuffer[0] == 0x100) {
    isRunning = 0;
}
```


- `0x303` - *SDL_TEXTINPUT*: Filtre les caractères et met à jour l'entrée utilisateur
```c
else if (eventBuffer[0] == 0x303) {
  local_30 = 0;
  while (sVar5 = strlen(pendingInput), local_30 < sVar5) {
    if (((inputLength < 0x40) &&
        (pcVar4 = strchr("FCSC{}abcdef0123456789",(int)pendingInput[local_30]),
        pcVar4 != (char *)0x0)) && (inputLength < 0xff)) {
      pcVar4 = &input + inputLength;
      inputLength = inputLength + 1;
      *pcVar4 = pendingInput[local_30];
      (&input)[inputLength] = 0;
    }
    local_30 = local_30 + 1;
  }
}
```
On voit déjà qu'on ne pourra entrer que les caractères `FCSC{}abcdef0123456789`.


- `0x300` - *SDL_KEYDOWN*: Définit des actions en fonction des touches pressées
```c
else if (eventBuffer[0] == 0x300) {
  if (((keyCode == 8) && ((keyMod & 0xc0) == 0)) && (inputLength != 0)) {
    puVar1 = &DAT_0036b25f + inputLength;
    inputLength = inputLength - 1;
    *puVar1 = 0;
  }
  else if ((keyCode == 0x71) && ((keyMod & 0xc0) != 0)) {
    isRunning = 0;
  }
  else if ((keyCode == 99) && ((keyMod & 0xc0) != 0)) {
    memset(&input,0,0x100);
    inputLength = 0;
  }
  else if ((keyCode == 8) && ((keyMod & 0xc0) != 0)) {
    memset(&input,0,0x100);
    inputLength = 0;
  }
  else if (keyCode == 0x1b) {
    memset(&input,0,0x100);
    inputLength = 0;
  }
  else if (keyCode == 0x20) {
    isAudioPaused = isAudioPaused ^ 1;
    SDL_PauseAudioDevice(audioDeviceId,isAudioPaused == 0);
  }
  else if (((keyCode == 0x76) && ((keyMod & 0xc0) != 0)) &&
          (local_60 = (char *)SDL_GetClipboardText(), local_60 != (char *)0x0)) {
    local_38 = 0;
    while (sVar5 = strlen(local_60), local_38 < sVar5) {
      if (((inputLength < 0x40) &&
          (pcVar4 = strchr("FCSC{}abcdef0123456789",(int)local_60[local_38]),
          pcVar4 != (char *)0x0)) && (inputLength < 0xff)) {
        pcVar4 = &input + inputLength;
        inputLength = inputLength + 1;
        *pcVar4 = local_60[local_38];
        (&input)[inputLength] = 0;
      }
      local_38 = local_38 + 1;
    }
    SDL_free(local_60);
  }
}
```

On voit plusieurs raccourcis qui sont définis: _CTRL+C_, _CTRL+V_, _CTRL+Q_...

### Vérification du flag

Dans un premier temps, le programme va vérifier le préfixe de notre entrée. S'il est correct, il appellera la fonction `checkFlagValidity()`.

```c
isPrefixCorrect =
   (uint)(((((input == 'F' && input_second_char == 'C') && input_third_char == 'S')
           && input_fourth_char == 'C') && input_fifth_char == '{') &&
         (&DAT_0036b25f)[inputLength] == '}');
isFlagValid = checkFlagValidity(renderer);
isPrefixCorrect = isFlagValid & isPrefixCorrect;
```

### Gestion du chronomètre

Ensuite, le programme va vérifier le temps passé. On a un timer de 60 secondes au maximum.

```c
sdlResult = SDL_GetTicks();
elapsedSeconds = (uint)(sdlResult - startTicks) / 1000;
if ((0x3b < elapsedSeconds) && (hasTimedOut == 0)) {
    hasTimedOut = 1;
}
```

On va pouvoir directement patcher cette variable pour rendre le timer inefficace, ce sera utile pour la suite:

```c
if ((0x3b < elapsedSeconds) && (hasTimedOut == 0)) {
    hasTimedOut = 0;
}
```

![breaking_the_timer.jpg](https://i.ibb.co/9mNsfQhf/breaking-the-timer.jpg)

### Changements d'image de fond

On remarque qu'en fonction de certains évènements, l'image de fond de l'application va changer, notamment quand le programme n'a _pas timeout_ mais que _l'entrée n'est pas correcte_:

```c
if (hasTimedOut == 0) {
    if (isPrefixCorrect == 0) {
      SDL_RenderCopy(renderer,bgTexture,0,&DAT_0010b410);
    }
}
```

Quand le programme n'a _pas timeout_ et que _l'entrée est correcte_:

```c
else {
  computeHash(&input,inputLength,local_138);
  if (DAT_0036b200 == 0) {
    updateHashTexture(renderer,&DAT_0036b200,local_138);
  }
  SDL_RenderCopy(renderer,DAT_0036b200,0,&DAT_0010b410);
}
```

Et enfin, quand le programme _a timeout_:

```c
  else {
    SDL_RenderCopy(renderer,timeoutTexture,0,&DAT_0010b410);
  }
```

Il affiche ensuite l'icône pour la musique ainsi que le temps restant, mais ça ne nous intéresse pas vraiment pour ce challenge.

## checkFlagValidity()

On va maintenant se pencher sur la fonction qui vérifie le flag, puisque c'est elle qui va nous permettre de comprendre comment avoir une entrée valide.

La manière dont il vérifie le flag est intéressante, on comprend assez vite le nom du challenge `coloratops`.

Le programme prépare une surface RGB qui va être utilisée pour lire un caractère de l'input:

```c
rectX = signatureIndex * 0x11 + 0x3c;
rectY = 0x25f;
surfacePtr = SDL_CreateRGBSurfaceWithFormat(0,0x10,0x20,0x20,0x16462004);
if (surfacePtr == 0) break;
local_98 = rectX;
local_94 = rectY;
rectW = 0x10;
rectH = 0x20;
SDL_RenderReadPixels
          (renderer,&local_98,**(undefined4 **)(surfacePtr + 8),
           *(undefined8 *)(surfacePtr + 0x20),*(undefined4 *)(surfacePtr + 0x18));
pixelDataPtr = *(long *)(surfacePtr + 0x20);
```

Il va ensuite extraire la `signature` de ce caractère pour remplir le tableau `extractedSignatures`:

```c
decodedSignature = 0xff; 
for (rowIndex = 0; rowIndex < 0x20; rowIndex = rowIndex + 1) { 
    for (colIndex = 0; colIndex < 0x10; colIndex = colIndex + 1) { 
        pixelValue = *(undefined4 *)(pixelDataPtr + (long)(colIndex + rowIndex * 0x10) * 4); 
        if (decodedSignature == 0xff) { 
            decodedSignature = decodePixelSignature(pixelValue); 
        } 
    } 
}
extractedSignatures[signatureIndex] = decodedSignature;
```

Enfin, il vérifie si le tableau de signatures est correct en le comparant à un tableau qui contient les signatures valides (`expectedSignatures`):

```c
if (0x3f < signatureIndex) {
  isValid = 1;
  for (compareIndex = 0; compareIndex < 0x40; compareIndex = compareIndex + 1) {
    isValid = isValid & (uint)extractedSignatures[compareIndex] ==
                        *(uint *)(&expectedSignatures + compareIndex * 4);
  }
  return isValid;
}
```

## Récupérer les signatures valides

Maintenant, il faut récupérer le tableau de signatures valides. Pour ce faire, on va déboguer le programme et inspecter la variable au moment de la comparaison.

On va d'abord s'arrêter à l'appel de `checkFlagValidity()`. Vu que le programme est **strippé**, on ne peut pas directement mettre le breakpoint avec le nom de la fonction, il faut chercher son appel en regardant le comportement de `main()`.

`checkFlagValidity()` -> `0x55555555dc77`

On voit ces instructions qui sont plutôt intéressantes: 
![2025-04-27-173526_755x281_scrot.png](https://i.ibb.co/PZs4DHHW/2025-04-27-173526-755x281-scrot.png)

On peut aller à l'instruction suivante et inspecter le contenu de `rax` pour voir notre tableau `expectedSignatures`:

![2025-04-27-173958_425x381_scrot.png](https://i.ibb.co/gLmq2YfF/2025-04-27-173958-425x381-scrot.png)

Et le transformer en une liste, ça sera utile pour plus tard:

```python
[0,0,0,0,   0,9,6,3,   6,7,6,5,   7,4,6,2,
7,7,2,9,   6,7,7,5,   1,6,2,8,   4,3,6,8,
5,4,9,2,   9,1,2,7,   1,1,4,4,   2,5,4,8,
6,1,6,7,   4,9,1,9,   5,4,3,9,   9,9,3,0]
```

## Comprendre le fonctionnement des signatures

Maintenant qu'on connaît les signatures nécessaires, il faut comprendre à quoi elles correspondent, car ces chiffres ne sont pas très parlants.

Regardons la fonction `decodePixelSignature()`

```c
ulong decodePixelSignature(int pixelValue)

{
  ulong index;
  
  index = 0;
  while( true ) {
    if (9 < index) {
      return 0xffffffff;
    }
    if (pixelValue == *(int *)(&DAT_0010b520 + index * 4)) break;
    index = index + 1;
  }
  return index;
}
```

Cette fonction va parcourir un tableau et retourner l'indice quand les couleurs correspondent.

On comprend donc notre tableau précédent, c'est un tableau d'indices !

Il faut donc savoir à quelle couleur correspond chaque indice. On va pouvoir faire ça avec GDB, sauf qu'une fois de plus le programme est **strippé** donc on ne peut pas juste mettre un _breakpoint_ sur la fonction.

![2025-04-27-180202_746x879_scrot.png](https://i.ibb.co/PGpGL06v/2025-04-27-180202-746x879-scrot.png)

On voit une instruction `call 0x55555555dc32` et la fonction à `0x55555555dc32` semble être notre `decodePixelSignature`.

La ligne `0x55555555dc4f: lea rax,[rip+0x18ca] # 0x55555555f520` est intéressante car c'est sûrement l'adresse du tableau qui contient les couleurs. Essayons d'inspecter sa valeur:

![2025-04-27-180603_764x88_scrot.png](https://i.ibb.co/7mRnDR2/2025-04-27-180603-764x88-scrot.png)

Et ces valeurs sont très cohérentes, puisque `0xffffffff` est le code hexadécimal pour du _blanc_.

|Indice|Valeur Hex|Nom de la couleur|
|---|---|---|
|0|0xffffffff|Blanc|
|1|0x802d2fff|Rouge bordeaux|
|2|0xff595eff|Rose vif|
|3|0xff924cff|Orange-corail|
|4|0xffae43ff|Orange doré|
|5|0xffca3aff|Jaune ambre|
|6|0x8ac926ff|Vert lime|
|7|0x52a675ff|Vert émeraude|
|8|0x6a4c93ff|Violet indigo|
|9|0x1982c4ff|Bleu azur|

## Solution colorée

Si on utilise ce tableau de correspondances des couleurs, on aura les couleurs du flag:

`⬜⬜⬜⬜⬜🔵🟢🟠🟢🟢🟢🟡🟢🟠🟢🟣🟢🟢🟣🔵🟢🟢🟢🟡🔴🟢🟣🟣🟠🟠🟢🟣🟡🟠🔵🟣🔵🔴🟣🟢🔴🔴🟠🟠🟣🟡🟠🟣🟢🔴🟢🟢🟠🔵🔴🔵🟡🟠🟠🔵🔵🔵🟠⬜`

On remarque quelque chose de très intéressant: **les 5 premiers caractères sont blancs**, si on teste ça dans le programme, cette contrainte est déjà respectée:

![2025-04-27-181716_1187x676_scrot.png](https://i.ibb.co/217tjyVQ/2025-04-27-181716-1187x676-scrot.png)

Trouver le flag revient donc à _trouver l'entrée qui aura les couleurs correspondantes à notre tableau_.

Deux options s'offrent à nous:

![bruteforce_ou_script.jpg](https://i.ibb.co/990f1pHm/bruteforce-ou-script.jpg)

Puisque _la couleur d'un caractère dépend du caractère suivant_, on peut commencer par la fin du flag et remonter au fur et à mesure jusqu'au début du flag. Par exemple, le seul caractère qui fait une accolade fermée blanche est la lettre _d_. On sait donc que le dernier caractère du flag est _d_.

![2025-04-27-182348_1169x141_scrot.png](https://i.ibb.co/pv6YDpkN/2025-04-27-182348-1169x141-scrot.png)

Pour vérifier notre input on peut mettre un breakpoint à `0x55555555dde1`, juste avant que le programme commence à comparer les signatures dans `checkFlagValidity()`.

Ensuite, on inspecte notre input comme ceci:

![2025-04-27-182943_779x206_scrot.png](https://i.ibb.co/Q3SpCRMc/2025-04-27-182943-779x206-scrot.png)

À la fin, on a `0x03` puis `0x00`. Si on reprend notre tableau `expectedSignatures`, on voit que les quatre dernières valeurs sont `[9,9,3,0]`. On retrouve bien notre `3` suivi de notre `0`.

## Résolution

Après environ une heure et demie à tester les couleurs et à ne pas faire la différence entre le orange corail, le orange doré et le jaune, on trouve enfin la bonne entrée:

![2025-04-27-183435_1194x677_scrot.png](https://i.ibb.co/b569TXYC/2025-04-27-183435-1194x677-scrot.png)

`⬜⬜⬜⬜⬜🔵🟢🟠🟢🟢🟢🟡🟢🟠🟢🟣🟢🟢🟣🔵🟢🟢🟢🟡🔴🟢🟣🟣🟠🟠🟢🟣🟡🟠🔵🟣🔵🔴🟣🟢🔴🔴🟠🟠🟣🟡🟠🟣🟢🔴🟢🟢🟠🔵🔴🔵🟡🟠🟠🔵🔵🔵🟠⬜`

Si on plisse les yeux, on voit que notre représentation colorée était plutôt fidèle (à quelques détails près) !

## Conclusion

J'ai adoré ce challenge ! En tant que débutant en reverse, j'ai appris beaucoup de choses et la touche colorée a rendu la résolution vraiment sympa.

![solving.gif](https://i.ibb.co/C5YxYhpy/solving.gif)

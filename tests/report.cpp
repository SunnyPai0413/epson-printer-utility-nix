// Regression checks for device reports; no hardware or protocol emulation.
#define main native_cli_main
#include "../src/cli.cpp"
#undef main
#include <cstdlib>
static void require(bool condition) { if (!condition) std::abort(); }
int main() {
    EPS_INK_INFO ink = {};
    for (auto v : sixInks(ink)) require(v.toObject()["reported_percent"].isNull());
    ink.number = 6; ink.showInkInfo = 1;
    for (int i = 0; i < 6; ++i) { ink.colors[i] = 5-i; ink.remaining[i] = 12+i; }
    auto result = sixInks(ink);
    require(result[0].toObject()["reported_percent"].toInt() == 17);
    require(result[5].toObject()["reported_percent"].toInt() == 12);
    ink.remaining[5] = 0;
    require(sixInks(ink)[0].toObject()["reported_percent"].toInt(-1) == 0);
    ink.remaining[5] = 105;
    require(sixInks(ink)[0].toObject()["reported_percent"].isNull());
    ink.remaining[5] = 25; ink.status[5] = -3;
    require(sixInks(ink)[0].toObject()["reported_percent"].isNull());
    ink.colors[5] = EPS_COLOR_PHOTOBLACK; ink.status[5] = 0;
    require(sixInks(ink)[0].toObject()["reported_percent"].toInt() == 25);
    ink.colors[4] = 0;
    require(sixInks(ink)[0].toObject()["reported_percent"].isNull());
    ink.showInkInfo = 0;
    for (auto v : sixInks(ink)) require(v.toObject()["reported_percent"].isNull());
}

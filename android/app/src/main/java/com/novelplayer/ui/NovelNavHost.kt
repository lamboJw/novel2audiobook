package com.novelplayer.ui

import androidx.compose.runtime.Composable
import androidx.navigation.NavHostController
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.navArgument

@Composable
fun NovelNavHost(navController: NavHostController) {
    NavHost(navController = navController, startDestination = "novel_list") {
        composable("novel_list") {
            NovelListScreen(
                onNovelClick = { novelId ->
                    navController.navigate("novel_detail/$novelId")
                }
            )
        }

        composable(
            route = "novel_detail/{novelId}",
            arguments = listOf(navArgument("novelId") { type = NavType.IntType })
        ) { backStackEntry ->
            val novelId = backStackEntry.arguments?.getInt("novelId") ?: return@composable
            NovelDetailScreen(
                novelId = novelId,
                onChapterClick = { chapterId ->
                    navController.navigate("player/$novelId/$chapterId")
                },
                onBack = { navController.popBackStack() }
            )
        }

        composable(
            route = "player/{novelId}/{chapterId}",
            arguments = listOf(
                navArgument("novelId") { type = NavType.IntType },
                navArgument("chapterId") { type = NavType.IntType }
            )
        ) { backStackEntry ->
            val novelId = backStackEntry.arguments?.getInt("novelId") ?: return@composable
            val chapterId = backStackEntry.arguments?.getInt("chapterId") ?: return@composable
            PlayerScreen(
                novelId = novelId,
                chapterId = chapterId,
                onBack = { navController.popBackStack() }
            )
        }
    }
}

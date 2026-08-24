option(${PROJECT_NAME}_ENABLE_CLANG_TIDY "Enable clang-tidy" ON)
option(${PROJECT_NAME}_ENABLE_CPPCHECK "Enable cppcheck" ON)

if(${PROJECT_NAME}_ENABLE_CLANG_TIDY)
  find_program(CLANGTIDY clang-tidy)
  if(CLANGTIDY)
    # Forward GCC's full preprocessor search list (libstdc++, multilib,
    # include-fixed, compiler builtins) to clang-tidy so headers like
    # stddef.h resolve under conda/pixi GCC sysroots (#211).
    include("${CMAKE_CURRENT_LIST_DIR}/ClangTidyIncludes.cmake")
    set(CMAKE_CXX_CLANG_TIDY
        ${CLANGTIDY}
        --extra-arg=-Wno-unknown-warning-option
        ${AGAMEMNON_CLANG_TIDY_EXTRA_ARGS})
    if(${PROJECT_NAME}_BUILD_TESTING)
      # Deferred so the test is registered after enable_testing() in the
      # top-level CMakeLists.txt (this module is included before it).
      cmake_language(DEFER DIRECTORY ${PROJECT_SOURCE_DIR}
        CALL add_test
          NAME clang_tidy_stddef_smoke
          COMMAND ${CMAKE_COMMAND}
            -DCLANG_TIDY_CMD=${CLANGTIDY}
            -DEXTRA_ARGS_FILE=${CMAKE_BINARY_DIR}/clang-tidy-extra-args.txt
            -DTU=${PROJECT_SOURCE_DIR}/test/clang_tidy_smoke_tu.cpp
            -P ${PROJECT_SOURCE_DIR}/test/cmake/clang_tidy_stddef_smoke.cmake)
    endif()
  else()
    message(WARNING "clang-tidy not found")
  endif()
endif()

if(${PROJECT_NAME}_ENABLE_CPPCHECK)
  find_program(CPPCHECK cppcheck)
  if(CPPCHECK)
    set(CMAKE_CXX_CPPCHECK ${CPPCHECK} --suppress=missingInclude --enable=all
                           --inline-suppr --inconclusive)
  else()
    message(WARNING "cppcheck not found")
  endif()
endif()
